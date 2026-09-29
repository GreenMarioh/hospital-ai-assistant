from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.services.scan import EICAR
from app.services.storage import LocalStorage
from tests.conftest import ADMIN, login_headers
from tests.helpers import by_email, link_doctor_patient

S, P1, P2, D1 = (
    "staff@hospital.example.com",
    "patient1@example.com",
    "patient2@example.com",
    "doctor1@hospital.example.com",
)
PDF = b"%PDF-1.4\n%test\n" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50


async def _pid(email=P1):
    from app.models import Patient

    return (await by_email(Patient, email)).id


def _up(
    client, pid, h, data=PDF, ctype="application/pdf", name="report.pdf", doc_type="lab_report"
):
    return client.post(
        f"/api/patients/{pid}/documents",
        headers=h,
        files={"file": (name, data, ctype)},
        data={"doc_type": doc_type},
    )


async def test_upload_list_download_roundtrip(client):
    pid, h = await _pid(), await login_headers(client, S)
    r = await _up(client, pid, h)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["size_bytes"] == len(PDF) and doc["filename"] == "report.pdf"
    assert len((await client.get(f"/api/patients/{pid}/documents", headers=h)).json()) == 1
    link = (await client.get(f"/api/documents/{doc['id']}/link", headers=h)).json()
    dl = await client.get(link["url"])  # signed link needs no bearer token
    assert dl.status_code == 200 and dl.content == PDF
    assert dl.headers["content-disposition"].startswith("attachment")
    assert (await client.delete(f"/api/documents/{doc['id']}", headers=h)).status_code == 204
    assert (await client.get(link["url"])).status_code == 404


@pytest.mark.parametrize(
    ("data", "ctype", "name", "code"),
    [
        (b"MZ\x90\x00" + b"0" * 50, "application/x-msdownload", "a.exe", 415),
        (b"<script>alert(1)</script>", "application/pdf", "fake.pdf", 415),  # magic bytes mismatch
        (PNG, "application/pdf", "png-as.pdf", 415),
        (b"", "application/pdf", "empty.pdf", 422),
        (b"%PDF-1.4 " + EICAR, "application/pdf", "virus.pdf", 422),
        (PDF + b"0" * (10 * 1024 * 1024), "application/pdf", "big.pdf", 413),
    ],
)
async def test_upload_validation(client, data, ctype, name, code):
    r = await _up(client, await _pid(), await login_headers(client, S), data, ctype, name)
    assert r.status_code == code, r.text


async def test_unknown_doc_type_rejected(client):
    r = await _up(client, await _pid(), await login_headers(client, S), doc_type="weird")
    assert r.status_code == 422


async def test_filename_is_sanitized(client):
    r = await _up(
        client, await _pid(), await login_headers(client, S), name="../../etc/pass wd?.pdf"
    )
    assert (
        r.status_code == 201
        and "/" not in r.json()["filename"]
        and ".." not in r.json()["filename"]
    )


async def test_document_access_control(client):
    pid = await _pid(P1)
    doc = (await _up(client, pid, await login_headers(client, S))).json()
    # owner can see; other patient/unrelated doctor/admin cannot
    assert (
        await client.get(
            f"/api/documents/{doc['id']}/link", headers=await login_headers(client, P1)
        )
    ).status_code == 200
    for email, pw in [(P2, None), (D1, None), (ADMIN[0], ADMIN[1])]:
        h = await login_headers(client, email, pw) if pw else await login_headers(client, email)
        assert (await client.get(f"/api/documents/{doc['id']}/link", headers=h)).status_code in (
            403,
            404,
        )
        assert (await client.get(f"/api/patients/{pid}/documents", headers=h)).status_code in (
            403,
            404,
        )
        assert (await _up(client, pid, h)).status_code in (403, 404)
    await link_doctor_patient(D1, P1)
    assert (
        await client.get(
            f"/api/documents/{doc['id']}/link", headers=await login_headers(client, D1)
        )
    ).status_code == 200


async def test_patient_can_upload_own_only(client):
    h = await login_headers(client, P1)
    assert (await _up(client, await _pid(P1), h, PNG, "image/png", "scan.png")).status_code == 201
    assert (await _up(client, await _pid(P2), h, PNG, "image/png", "scan.png")).status_code == 404


async def test_signed_link_tampered_expired_wrong_type(client):
    key = get_settings().secret_key
    now = datetime.now(UTC)
    bad = [
        "garbage",
        jwt.encode(
            {"doc": "x", "type": "download", "exp": now + timedelta(minutes=1)},
            "wrong-key" * 5,
            "HS256",
        ),
        jwt.encode(
            {
                "doc": "00000000-0000-0000-0000-000000000000",
                "type": "download",
                "exp": now - timedelta(seconds=5),
            },
            key,
            "HS256",
        ),
        jwt.encode(
            {
                "doc": "00000000-0000-0000-0000-000000000000",
                "type": "access",
                "exp": now + timedelta(minutes=1),
            },
            key,
            "HS256",
        ),
    ]
    for t in bad:
        assert (await client.get("/api/documents/download", params={"token": t})).status_code == 403
    ok_token = jwt.encode(
        {
            "doc": "00000000-0000-0000-0000-000000000000",
            "type": "download",
            "exp": now + timedelta(minutes=1),
        },
        key,
        "HS256",
    )
    assert (
        await client.get("/api/documents/download", params={"token": ok_token})
    ).status_code == 404


async def test_admin_cannot_view_documents(client):
    h = await login_headers(client, ADMIN[0], ADMIN[1])
    assert (
        await client.get(f"/api/patients/{await _pid()}/documents", headers=h)
    ).status_code == 403


async def test_local_storage_rejects_traversal(tmp_path):
    st = LocalStorage(str(tmp_path))
    await st.put("a/b.bin", b"x", "application/octet-stream")
    assert await st.get("a/b.bin") == b"x"
    with pytest.raises(ValueError):
        await st.get("../../etc/passwd")
    await st.delete("a/b.bin")
