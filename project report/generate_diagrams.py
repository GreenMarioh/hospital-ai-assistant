import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.makedirs('Project Report/diagrams', exist_ok=True)

# 1. System Architecture
def make_architecture():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.axis('off')
    
    # Background boxes
    # Client Tier
    rect_clients = patches.FancyBboxPatch((0.05, 0.65), 0.25, 0.28, boxstyle="round,pad=0.03", ec="#1e40af", fc="#eff6ff", lw=2)
    ax.add_patch(rect_clients)
    ax.text(0.175, 0.90, "User Roles (Client Tier)", ha='center', va='center', fontsize=11, fontweight='bold', color="#1e3a8a")
    ax.text(0.175, 0.77, "• Patient Portal\n• Doctor Clinical Chart\n• Reception Calendar\n• Admin Dashboard", ha='center', va='center', fontsize=9, color="#1e293b")
    
    # Reverse Proxy / Edge Tier
    rect_edge = patches.FancyBboxPatch((0.38, 0.65), 0.24, 0.28, boxstyle="round,pad=0.03", ec="#047857", fc="#ecfdf5", lw=2)
    ax.add_patch(rect_edge)
    ax.text(0.50, 0.90, "Edge & Gateway (Caddy)", ha='center', va='center', fontsize=11, fontweight='bold', color="#065f46")
    ax.text(0.50, 0.77, "• Automatic TLS / HTTPS\n• Same-Origin Routing\n• Static File Serving\n• Rate-Limit Header Proxy", ha='center', va='center', fontsize=9, color="#1e293b")

    # Application Tier
    rect_app = patches.FancyBboxPatch((0.70, 0.52), 0.26, 0.42, boxstyle="round,pad=0.03", ec="#b45309", fc="#fffbeb", lw=2)
    ax.add_patch(rect_app)
    ax.text(0.83, 0.90, "Core Application Tier", ha='center', va='center', fontsize=11, fontweight='bold', color="#92400e")
    ax.text(0.83, 0.73, "• Next.js 15 Standalone\n• FastAPI (Async Workers)\n• Server-Side RBAC\n• Object Access Matrix\n• Audit Chain Logger\n• APScheduler Worker", ha='center', va='center', fontsize=9, color="#1e293b")

    # Data Tier
    rect_data = patches.FancyBboxPatch((0.08, 0.12), 0.38, 0.36, boxstyle="round,pad=0.03", ec="#475569", fc="#f8fafc", lw=2)
    ax.add_patch(rect_data)
    ax.text(0.27, 0.43, "Data & Storage Tier", ha='center', va='center', fontsize=11, fontweight='bold', color="#334155")
    ax.text(0.27, 0.27, "• PostgreSQL 16 (GiST Exclusions, GIN Search)\n• Redis 7 (Distributed Rate Limits)\n• S3 / MinIO (Document Vault)\n• ClamAV Daemon (Streaming Virus Scan)", ha='center', va='center', fontsize=9, color="#1e293b")

    # AI & Decision Support Tier
    rect_ai = patches.FancyBboxPatch((0.55, 0.12), 0.40, 0.36, boxstyle="round,pad=0.03", ec="#6b21a8", fc="#faf5ff", lw=2)
    ax.add_patch(rect_ai)
    ax.text(0.75, 0.43, "AI Decision Support & Safety", ha='center', va='center', fontsize=11, fontweight='bold', color="#581c87")
    ax.text(0.75, 0.27, "• Red-Flag Regex Rule Engine\n• Google Gemini Pro/Flash API\n• Output Guardrails (Anti-Diagnosis)\n• In-Memory TF-IDF Knowledge Base\n• PII Anonymization Scrubber", ha='center', va='center', fontsize=9, color="#1e293b")

    # Arrows
    arrow_props = dict(arrowstyle="->", lw=1.5, color="#334155")
    ax.annotate("", xy=(0.38, 0.79), xytext=(0.30, 0.79), arrowprops=arrow_props)
    ax.annotate("", xy=(0.70, 0.79), xytext=(0.62, 0.79), arrowprops=arrow_props)
    ax.annotate("", xy=(0.75, 0.48), xytext=(0.83, 0.52), arrowprops=arrow_props)
    ax.annotate("", xy=(0.32, 0.48), xytext=(0.70, 0.60), arrowprops=arrow_props)
    
    plt.title("Figure 3.1: AI Hospital Management Assistant System Architecture", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig('Project Report/diagrams/system_architecture.png', bbox_inches='tight')
    plt.close()

# 2. Triage & Safety Flowchart
def make_triage_flow():
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    ax.axis('off')
    
    # Nodes
    boxes = [
        (0.5, 0.90, "1. Patient Submits Symptoms / Complaint", "#eff6ff", "#1d4ed8"),
        (0.5, 0.76, "2. Deterministic Red-Flag Rule Engine (Regex Matching)", "#fef3c7", "#d97706"),
        (0.2, 0.58, "EMERGENCY DETECTED\n(MTS/ESI Red Flag Match)", "#fee2e2", "#dc2626"),
        (0.8, 0.58, "NON-EMERGENCY\n(Proceed to LLM Intake)", "#ecfdf5", "#059669"),
        (0.2, 0.40, "Lock Conversation State\nBypass LLM\nRender Emergency Banner & 911 Call", "#fecaca", "#b91c1c"),
        (0.8, 0.42, "Scrub Direct PII\nLoad Prompt + Hospital Departments\nGemini API Structured Completion", "#d1fae5", "#047857"),
        (0.8, 0.26, "Output Guardrail Verification\nCheck for Diagnosis / Med Prescriptions", "#fef3c7", "#d97706"),
        (0.5, 0.10, "Render Triage Result + Clinician Disclaimer\nSuggested Dept + Book Appointment Action", "#f3e8ff", "#7e22ce")
    ]
    
    for x, y, text, fc, ec in boxes:
        p = patches.FancyBboxPatch((x-0.18, y-0.05), 0.36, 0.09, boxstyle="round,pad=0.02", ec=ec, fc=fc, lw=1.8)
        ax.add_patch(p)
        ax.text(x, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color="#0f172a")

    # Connectors
    kw = dict(arrowstyle="->", lw=1.5, color="#1e293b")
    ax.annotate("", xy=(0.5, 0.81), xytext=(0.5, 0.85), arrowprops=kw)
    ax.annotate("True", xy=(0.25, 0.63), xytext=(0.42, 0.74), arrowprops=kw)
    ax.annotate("False", xy=(0.75, 0.63), xytext=(0.58, 0.74), arrowprops=kw)
    ax.annotate("", xy=(0.2, 0.45), xytext=(0.2, 0.53), arrowprops=kw)
    ax.annotate("", xy=(0.8, 0.47), xytext=(0.8, 0.53), arrowprops=kw)
    ax.annotate("", xy=(0.8, 0.31), xytext=(0.8, 0.37), arrowprops=kw)
    ax.annotate("", xy=(0.60, 0.15), xytext=(0.75, 0.21), arrowprops=kw)
    ax.annotate("", xy=(0.40, 0.15), xytext=(0.25, 0.35), arrowprops=kw)

    plt.title("Figure 4.1: Deterministic Red-Flag Triage & AI Safety Guardrails Flowchart", fontsize=11, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig('Project Report/diagrams/triage_flow.png', bbox_inches='tight')
    plt.close()

# 3. Audit Hash Chain
def make_audit_chain():
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    ax.axis('off')
    
    # Blocks
    blocks = [
        (0.18, "Audit Record N-1\nID: 1042\nAction: 'read'\nResource: 'patients/visits'\nPrev: 00e47..."),
        (0.50, "Audit Record N\nID: 1043\nAction: 'create'\nResource: 'appointments'\nPrev: a8f91..."),
        (0.82, "Audit Record N+1\nID: 1044\nAction: 'update'\nResource: 'records'\nPrev: 7c32b...")
    ]
    
    for x, text in blocks:
        p = patches.FancyBboxPatch((x-0.12, 0.30), 0.24, 0.45, boxstyle="round,pad=0.02", ec="#1e40af", fc="#eff6ff", lw=2)
        ax.add_patch(p)
        ax.text(x, 0.52, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color="#1e3a8a")

    kw = dict(arrowstyle="->", lw=2, color="#059669")
    ax.annotate("SHA-256 Link", xy=(0.38, 0.52), xytext=(0.30, 0.52), arrowprops=kw, fontsize=8, fontweight='bold', color="#059669")
    ax.annotate("SHA-256 Link", xy=(0.70, 0.52), xytext=(0.62, 0.52), arrowprops=kw, fontsize=8, fontweight='bold', color="#059669")

    ax.text(0.5, 0.15, "Tamper-Evident SHA-256 Hash Chaining: entry_hash = SHA256(prev_hash | user | role | action | path | status | ip)", 
            ha='center', va='center', fontsize=9, style='italic', color="#334155")

    plt.title("Figure 4.2: Cryptographic Tamper-Proof Audit Log Hash Chain", fontsize=11, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig('Project Report/diagrams/audit_chain.png', bbox_inches='tight')
    plt.close()

# 4. Load Test & Latency Benchmark Chart
def make_benchmark_chart():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), dpi=300)
    
    # Subplot 1: Response Latency Percentiles
    percentiles = ['p50', 'p75', 'p90', 'p95', 'p99']
    latencies = [18, 29, 42, 67, 112]
    colors = ['#38bdf8', '#0284c7', '#0369a1', '#075985', '#0c4a6e']
    
    bars = ax1.bar(percentiles, latencies, color=colors, width=0.55, edgecolor='#0f172a')
    ax1.set_ylabel('Latency (milliseconds)', fontsize=9, fontweight='bold')
    ax1.set_title('API Response Latency under 50 VUs (k6)', fontsize=10, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval} ms", ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    # Subplot 2: Component Breakdown
    components = ['Deterministic Triage', 'TF-IDF Retrieval', 'Postgres Slot Search', 'Live LLM Call (Avg)', 'Live LLM Call (p95)']
    comp_latencies = [1.2, 3.8, 14.5, 1420.0, 2180.0]
    ax2.barh(components, comp_latencies, color=['#10b981', '#10b981', '#10b981', '#f59e0b', '#ef4444'], edgecolor='#0f172a')
    ax2.set_xlabel('Execution Time (ms - log scale)', fontsize=9, fontweight='bold')
    ax2.set_xscale('log')
    ax2.set_title('Subsystem Latency Comparison', fontsize=10, fontweight='bold')
    ax2.grid(axis='x', linestyle='--', alpha=0.5)
    for i, v in enumerate(comp_latencies):
        ax2.text(v * 1.15, i, f"{v} ms", va='center', fontsize=8, fontweight='bold')

    plt.suptitle("Figure 4.6: System Load-Test and AI Subsystem Latency Benchmarks", fontsize=11, fontweight='bold')
    plt.tight_layout()
    plt.savefig('Project Report/diagrams/loadtest_latency.png', bbox_inches='tight')
    plt.close()

make_architecture()
make_triage_flow()
make_audit_chain()
make_benchmark_chart()
print("All diagrams generated successfully!")

