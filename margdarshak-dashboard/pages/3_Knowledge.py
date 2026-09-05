import csv
from datetime import date, datetime, timezone
from io import BytesIO, StringIO
from typing import Any
import uuid

import streamlit as st

from services.api_client import (
    APIClientError,
    InvalidCSVError,
    ShortlistValidationError,
    get_admin_overview,
    get_backend_health,
    get_knowledge,
    import_shortlist,
    patch_knowledge_status,
    post_knowledge_policy,
    preview_shortlist,
)

st.set_page_config(
    page_title="Knowledge Approval — Margdarshak AI",
    page_icon=":material/menu_book:",
    layout="wide",
)

# Admin Design System (§65):
# Background: Light grey / blue-grey (#F8FAFC)
# Primary: Dark charcoal (#0F172A / #1E293B)
# Accent: Muted green (#2E7D32 / #166534)
# Cards: Simple borders (#E2E8F0), minimal shadows, compact operational layout
KNOWLEDGE_CSS = """
<style>
    /* Base background and text tokens */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Header layout (§47) */
    .knowledge-header-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.25rem 0;
        padding: 0;
    }
    
    .knowledge-header-subtitle {
        font-size: 0.95rem;
        color: #475569;
        margin: 0 0 1.25rem 0;
    }

    /* System status badges */
    .status-badge-connected {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-badge-connected::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #22C55E;
    }
    .status-badge-offline {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-badge-offline::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #EF4444;
    }

    /* Section headers */
    .admin-section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        margin: 1.25rem 0 0.6rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Lifecycle Status Pills (§49) */
    .lifecycle-pill {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
    }
    .lifecycle-pill.draft {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .lifecycle-pill.published {
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
    }
    .lifecycle-pill.expired {
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }

    /* Type Pill */
    .doc-type-pill {
        display: inline-block;
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
    }

    /* Knowledge Card */
    .knowledge-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        transition: border-color 0.15s ease;
    }
    .knowledge-card:hover {
        border-color: #CBD5E1;
    }
    .knowledge-card.draft-card {
        border-left: 4px solid #F59E0B;
    }
    .knowledge-card.published-card {
        border-left: 4px solid #16A34A;
    }
    .knowledge-card.expired-card {
        border-left: 4px solid #DC2626;
    }

    .knowledge-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0F172A;
        margin: 0 0 0.35rem 0;
    }
    .knowledge-meta {
        font-size: 0.82rem;
        color: #64748B;
        display: flex;
        flex-wrap: wrap;
        gap: 0.9rem;
        align-items: center;
        margin-bottom: 0.6rem;
    }
    .knowledge-meta strong {
        color: #1E293B;
    }

    /* Content Box */
    .knowledge-content-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 5px;
        padding: 0.75rem 0.9rem;
        font-size: 0.83rem;
        color: #334155;
        margin-top: 0.5rem;
        line-height: 1.5;
    }
    .knowledge-content-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.6rem;
        margin-bottom: 0.4rem;
    }
    .knowledge-content-field {
        font-size: 0.8rem;
    }
    .knowledge-content-field-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #64748B;
    }

    /* Empty state */
    .empty-state-box {
        background-color: #FFFFFF;
        border: 1px dashed #CBD5E1;
        border-radius: 6px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        color: #64748B;
        margin: 1.5rem 0;
    }

    /* Summary metric card */
    .summary-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .summary-val {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }
    .summary-lbl {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-top: 0.15rem;
    }

    /* Section 67 Alert States */
    .section67-alert-error {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 4px solid #DC2626;
        border-radius: 6px;
        padding: 0.85rem 1.1rem;
        color: #991B1B;
        margin: 0.85rem 0;
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .section67-alert-error .alert-title {
        font-size: 0.96rem;
        font-weight: 700;
        color: #7F1D1D;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .section67-alert-success {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 4px solid #16A34A;
        border-radius: 6px;
        padding: 0.85rem 1.1rem;
        color: #166534;
        margin: 0.85rem 0;
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .section67-alert-success .alert-title {
        font-size: 0.96rem;
        font-weight: 700;
        color: #14532D;
        margin-bottom: 0.25rem;
    }

    /* Shortlist Preview Table */
    .preview-table-wrapper {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        overflow-x: auto;
        max-height: 380px;
        overflow-y: auto;
        margin: 0.75rem 0;
    }
    .preview-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
        text-align: left;
    }
    .preview-table th {
        background-color: #F8FAFC;
        color: #475569;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.72rem;
        padding: 0.6rem 0.8rem;
        border-bottom: 1px solid #E2E8F0;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .preview-table td {
        padding: 0.55rem 0.8rem;
        border-bottom: 1px solid #F1F5F9;
        color: #1E293B;
    }
    .preview-table tr:hover td {
        background-color: #F8FAFC;
    }

    /* Confirmation Card */
    .import-confirm-card {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 4px solid #2563EB;
        border-radius: 6px;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    /* Knowledge Library Table (§53) */
    .knowledge-table-wrapper {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        overflow-x: auto;
        margin: 0.85rem 0;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .knowledge-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.83rem;
        text-align: left;
    }
    .knowledge-table th {
        background-color: #F8FAFC;
        color: #475569;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.72rem;
        padding: 0.65rem 0.9rem;
        border-bottom: 2px solid #E2E8F0;
        white-space: nowrap;
    }
    .knowledge-table td {
        padding: 0.65rem 0.9rem;
        border-bottom: 1px solid #F1F5F9;
        color: #1E293B;
        vertical-align: middle;
    }
    .knowledge-table tr:hover td {
        background-color: #F8FAFC;
    }
</style>
"""
st.markdown(KNOWLEDGE_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Backend Connection Health Check
# ----------------------------------------------------------------------
backend_connected = False
try:
    health = get_backend_health()
    backend_connected = health.get("status") == "ok"
except APIClientError:
    backend_connected = False


# ----------------------------------------------------------------------
# Header Section (§47)
# ----------------------------------------------------------------------
hdr_col1, hdr_col2 = st.columns([4, 1.2])
with hdr_col1:
    st.markdown('<div class="knowledge-header-title">Knowledge Approval</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="knowledge-header-subtitle">Review policy versions before they become student-facing guidance.</div>',
        unsafe_allow_html=True,
    )
with hdr_col2:
    if backend_connected:
        st.markdown(
            '<div style="text-align: right; padding-top: 0.35rem;"><span class="status-badge-connected">Backend connected</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align: right; padding-top: 0.35rem;"><span class="status-badge-offline">Backend offline</span></div>',
            unsafe_allow_html=True,
        )

if not backend_connected:
    st.error(
        "Knowledge unavailable: Backend service is unreachable (http://127.0.0.1:8000). "
        "Ensure the FastAPI server is running and refresh.",
        icon=":material/cloud_off:",
    )


# ----------------------------------------------------------------------
# Data Fetching (Cached with Manual Refresh)
# ----------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def load_knowledge_library() -> list[dict[str, Any]]:
    return get_knowledge()


@st.cache_data(ttl=30, show_spinner=False)
def load_drives() -> list[dict[str, Any]]:
    try:
        overview = get_admin_overview()
        return overview.get("active_drives", [])
    except Exception:
        return []


try:
    with st.spinner("Searching approved placement information..."):
        knowledge_docs = load_knowledge_library() if backend_connected else []
except Exception:
    st.warning(
        "Knowledge unavailable: We couldn't load approved placement information. Please try again.",
        icon=":material/warning:",
    )
    knowledge_docs = []


active_drives = load_drives() if backend_connected else []


# ----------------------------------------------------------------------
# Main Navigation Tabs: 1) Policy Approval & Ingestion, 2) Knowledge Library
# ----------------------------------------------------------------------
tab_form, tab_import, tab_library = st.tabs([
    "➕ Create Policy Draft (§48)",
    "📥 Import Shortlist (§50–52)",
    "📚 Knowledge Library & Lifecycle (§49, §53)",
])



# ======================================================================
# TAB 1: Create Policy Draft (§48)
# ======================================================================
with tab_form:
    st.markdown(
        '<div class="admin-section-header">📄 Policy Draft Form (Spec §48)</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Fill out the placement drive guidelines below. Saving as Draft stores the policy in "
        "a pending state without surfacing it as live student guidance until approved."
    )

    with st.form("policy_draft_form", clear_on_submit=False):
        # Row 1: Placement Drive, Source Title
        col_drive, col_title = st.columns([1.2, 1.8])
        
        drive_options = ["(Custom / Other Company)"] + [
            f"{d.get('company_name', 'Unknown')}" for d in active_drives if d.get("company_name")
        ]
        
        with col_drive:
            selected_drive_label = st.selectbox(
                "Placement Drive *",
                options=drive_options,
                index=1 if len(drive_options) > 1 else 0,
                help="Select an active placement drive or enter custom company information",
            )
            custom_company = ""
            selected_drive_id = None
            if selected_drive_label == "(Custom / Other Company)":
                custom_company = st.text_input(
                    "Company Name *",
                    placeholder="e.g. Acme Cloud Systems",
                )
            else:
                custom_company = selected_drive_label
                # Find matching drive_id if available
                for d in active_drives:
                    if d.get("company_name") == selected_drive_label:
                        selected_drive_id = d.get("id")
                        break

        with col_title:
            source_title = st.text_input(
                "Source Title *",
                value=f"{custom_company} Placement Notice" if custom_company else "",
                placeholder="e.g. Acme Cloud Systems Placement Notice",
                help="Human-readable title of the source announcement or notice",
            )

        # Row 2: Source Reference, Version Label
        col_ref, col_ver = st.columns([2, 1])
        with col_ref:
            source_reference = st.text_input(
                "Source Reference *",
                value="manual://coordinator-entry",
                placeholder="e.g. manual://coordinator-entry or doc://portal/notice-2026",
                help="URI or provenance identifier for the policy source document",
            )
        with col_ver:
            version_label = st.text_input(
                "Version Label *",
                value="2026.1",
                placeholder="e.g. 2026.1",
                help="Semantic or institutional version tag",
            )

        st.markdown("<hr style='margin: 0.75rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)

        # Row 3: Eligibility, Salary/CTC
        col_elig, col_ctc = st.columns([2, 1])
        with col_elig:
            eligibility = st.text_area(
                "Eligibility Criteria *",
                placeholder="e.g. Final-year CSE/IT students; CGPA 7.5+; no active backlogs.",
                help="Specific criteria determining who can apply",
                height=85,
            )
        with col_ctc:
            salary_ctc = st.text_input(
                "Salary / CTC",
                placeholder="e.g. 14 LPA (Base: 11 LPA + 3 LPA Joining)",
                help="Total compensation and package details",
            )

        # Row 4: Application Deadline, Application URL
        col_dead, col_url = st.columns([1, 2])
        with col_dead:
            deadline_date = st.date_input(
                "Application Deadline",
                value=date.today(),
                help="Final date for student submissions",
            )
            deadline_str = deadline_date.isoformat() if deadline_date else ""
        with col_url:
            application_url = st.text_input(
                "Application URL",
                placeholder="https://careers.company.com/apply or placement portal link",
                help="Authoritative URL where students submit their application",
            )

        # Row 5: Instructions
        instructions = st.text_area(
            "Instructions & Guidelines",
            placeholder="e.g. Complete resume upload and coding assessment on HackerRank before the deadline. Do not use personal email.",
            help="Important instructions and guidelines for applicants",
            height=90,
        )

        st.markdown("<hr style='margin: 0.75rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)

        # Form Actions (§48)
        col_draft_btn, col_pub_btn, col_spacer = st.columns([1.5, 1.5, 3])
        with col_draft_btn:
            save_draft = st.form_submit_button(
                "💾 Save as Draft",
                type="primary",
                use_container_width=True,
                help="Saves the policy with status 'draft' for internal review",
            )
        with col_pub_btn:
            save_publish = st.form_submit_button(
                "🚀 Publish Immediately",
                use_container_width=True,
                help="Saves and immediately publishes the policy for student guidance",
            )

        if save_draft or save_publish:
            target_status = "draft" if save_draft else "published"
            
            # Validation
            validation_errors = []
            if not custom_company.strip():
                validation_errors.append("Placement Drive / Company name is required.")
            if not source_title.strip():
                validation_errors.append("Source Title is required.")
            if not source_reference.strip():
                validation_errors.append("Source Reference is required.")
            if not version_label.strip():
                validation_errors.append("Version Label is required.")
            if not eligibility.strip():
                validation_errors.append("Eligibility criteria is required.")

            if validation_errors:
                for err in validation_errors:
                    st.error(f"❌ {err}")
            elif not backend_connected:
                st.error("Cannot submit policy: Backend service is currently offline.")
            else:
                payload = {
                    "title": source_title.strip(),
                    "document_type": "placement_policy",
                    "company_name": custom_company.strip(),
                    "drive_id": selected_drive_id,
                    "version_label": version_label.strip(),
                    "source_reference": source_reference.strip(),
                    "status": target_status,
                    "content": {
                        "eligibility": eligibility.strip(),
                        "salary_ctc": salary_ctc.strip(),
                        "deadline": deadline_str,
                        "application_url": application_url.strip(),
                        "instructions": instructions.strip(),
                    },
                }

                try:
                    with st.spinner("Saving approved placement information..."):
                        resp = post_knowledge_policy(payload)
                        doc_id = resp.get("id", "created")
                        st.success(
                            f"✅ Policy '{source_title}' successfully saved with status **{target_status.upper()}** (ID: `{doc_id}`)! "
                            "It has been added to the knowledge lifecycle library.",
                            icon=":material/check_circle:",
                        )
                        load_knowledge_library.clear()
                        st.rerun()
                except APIClientError:
                    st.error("We couldn't save the placement policy. Please verify the fields and try again.", icon=":material/error:")



# ======================================================================
# TAB 2: Shortlist Ingestion & Import Workflow (§50, §51, §52, §67)
# ======================================================================
with tab_import:
    st.markdown(
        '<div class="admin-section-header">📥 Shortlist Spreadsheet Ingestion (Spec §§50–52)</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Upload company shortlist spreadsheets (.csv or .xlsx). The system validates all 8 required "
        "columns (§51), provides an interactive preview of parsed student records, and allows coordinator confirmation "
        "before publishing to the student knowledge base."
    )

    REQUIRED_SHORTLIST_COLUMNS = [
        "name", "enrollment_number", "email", "company", "drive_id", "shortlisted", "role", "round"
    ]

    # Sample template download helper
    with st.expander("ℹ️ Shortlist Spreadsheet Specifications & Sample Template (§51)", expanded=False):
        st.markdown(
            """
            Per **Spec §51**, every shortlist file must contain the following **8 required columns** (case-insensitive):
            - `name` — Full student name
            - `enrollment_number` — University roll / enrollment number
            - `email` — Student email address
            - `company` — Company name
            - `drive_id` — Associated placement drive identifier
            - `shortlisted` — Boolean / status string (`yes`/`no`, `true`/`false`, `shortlisted`)
            - `role` — Job role / profile
            - `round` — Interview or assessment round (e.g. `Technical Round 1`, `HR`)
            """
        )
        sample_csv = (
            "name,enrollment_number,email,company,drive_id,shortlisted,role,round\n"
            "Aarav Sharma,230611,aarav@example.edu,Riverbank Fintech Labs,drive-1,yes,Software Engineer,Technical Round 1\n"
            "Ananya Verma,230612,ananya@example.edu,Riverbank Fintech Labs,drive-1,yes,Software Engineer,Technical Round 1\n"
            "Rohan Gupta,230613,rohan@example.edu,Riverbank Fintech Labs,drive-1,no,Software Engineer,Technical Round 1\n"
        )
        st.download_button(
            "📥 Download Sample CSV Template",
            data=sample_csv,
            file_name="sample_shortlist_template.csv",
            mime="text/csv",
        )

    # ------------------------------------------------------------------
    # Step 1: ImportForm Metadata (Spec §50)
    # ------------------------------------------------------------------
    st.markdown('<div class="admin-section-header" style="margin-top: 1rem;">1. Import Details (§50)</div>', unsafe_allow_html=True)
    
    col_d, col_t = st.columns([1.2, 1.8])
    with col_d:
        import_drive_options = ["(Custom / Other Drive)"] + [
            f"{d.get('company_name', 'Unknown')}" for d in active_drives if d.get("company_name")
        ]
        selected_import_drive = st.selectbox(
            "Import for Drive *",
            options=import_drive_options,
            index=1 if len(import_drive_options) > 1 else 0,
            key="import_drive_select",
            help="Placement drive this shortlist belongs to (§50)",
        )
        custom_import_drive = ""
        resolved_company = ""
        resolved_drive_id = ""
        if selected_import_drive == "(Custom / Other Drive)":
            custom_import_drive = st.text_input(
                "Company / Drive Name *",
                placeholder="e.g. Acme Cloud Systems",
                key="custom_import_drive_input",
            )
            resolved_company = custom_import_drive.strip()
        else:
            resolved_company = selected_import_drive
            for d in active_drives:
                if d.get("company_name") == selected_import_drive:
                    resolved_drive_id = str(d.get("id") or "")
                    break

    with col_t:
        default_title = f"{resolved_company} — Shortlist" if resolved_company else ""
        import_title = st.text_input(
            "Import Title *",
            value=default_title,
            placeholder="e.g. Acme Cloud Systems — Technical Shortlist",
            key="import_title_input",
            help="Human-readable title for the shortlist knowledge document (§50)",
        )

    col_r, col_v = st.columns([2, 1])
    with col_r:
        default_ref = f"spreadsheet://placement/{resolved_company.lower().replace(' ', '-')}-shortlist" if resolved_company else "spreadsheet://coordinator-import"
        import_source_ref = st.text_input(
            "Source Reference *",
            value=default_ref,
            placeholder="e.g. spreadsheet://placement-cell/shortlist-2026",
            key="import_ref_input",
            help="Source spreadsheet URI or provenance reference (§50)",
        )
    with col_v:
        import_version_prefix = st.text_input(
            "Version Prefix *",
            value="2026.1",
            placeholder="e.g. 2026.1",
            key="import_version_input",
            help="Institutional or seasonal version label (§50)",
        )

    # ------------------------------------------------------------------
    # Step 2: File Upload (Spec §50)
    # ------------------------------------------------------------------
    st.markdown('<div class="admin-section-header" style="margin-top: 1.25rem;">2. Upload Spreadsheet (§50)</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload Shortlist File (CSV or XLSX)",
        type=["csv", "xlsx"],
        key="shortlist_file_uploader",
        help="Upload CSV or XLSX containing student shortlisting records. Max size: 5 MB.",
    )

    # ------------------------------------------------------------------
    # Step 3 & 4: Parse & Validate Columns -> Show Section 67 Errors
    # ------------------------------------------------------------------
    parsed_rows: list[dict[str, Any]] | None = None
    parsing_error_type: str | None = None
    parsing_error_message: str | None = None
    missing_cols_list: list[str] = []

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name.lower()

        if len(file_bytes) > 5_000_000:
            parsing_error_type = "invalid_csv"
            parsing_error_message = "File exceeds the maximum limit of 5 MB."
        else:
            # First try calling the backend preview route
            try:
                preview_data = preview_shortlist(file_bytes, uploaded_file.name)
                parsed_rows = preview_data.get("rows", [])
            except ShortlistValidationError as exc:
                parsing_error_type = "missing_fields"
                parsing_error_message = str(exc)
                missing_cols_list = exc.missing_columns
            except InvalidCSVError as exc:
                parsing_error_type = "invalid_csv"
                parsing_error_message = str(exc)
            except Exception:
                # If backend is unreachable, perform local validation fallback
                try:
                    if filename.endswith(".csv"):
                        decoded = file_bytes.decode("utf-8-sig")
                        reader = csv.DictReader(StringIO(decoded))
                        raw_rows = list(reader)
                        if not raw_rows:
                            parsing_error_type = "invalid_csv"
                            parsing_error_message = "The uploaded CSV file is empty."
                        else:
                            normalized_rows = [
                                {str(k).strip().lower(): ("" if v is None else str(v).strip()) for k, v in row.items()}
                                for row in raw_rows
                                if any(val not in (None, "") for val in row.values())
                            ]
                            found_cols = set(normalized_rows[0].keys()) if normalized_rows else set()
                            missing = sorted(set(REQUIRED_SHORTLIST_COLUMNS) - found_cols)
                            if missing:
                                parsing_error_type = "missing_fields"
                                missing_cols_list = missing
                                parsing_error_message = f"Missing required columns: {', '.join(missing)}"
                            else:
                                parsed_rows = normalized_rows
                    else:
                        parsing_error_type = "invalid_csv"
                        parsing_error_message = "Backend offline; please ensure CSV format is used."
                except Exception as local_err:
                    parsing_error_type = "invalid_csv"
                    parsing_error_message = f"Failed to parse CSV file: {local_err}"

    # Render Section 67 Error States if parsing/validation failed
    if parsing_error_type == "invalid_csv":
        st.markdown(
            f"""
            <div class="section67-alert-error">
                <div class="alert-title">❌ Invalid CSV</div>
                <div>
                    We couldn't read that shortlist file. Please ensure the file is a properly formatted CSV (UTF-8) or XLSX spreadsheet, and is smaller than 5 MB.<br/>
                    <small style="color: #B91C1C;">Details: {parsing_error_message}</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif parsing_error_type == "missing_fields":
        missing_display = ", ".join(missing_cols_list) if missing_cols_list else "one or more required columns"
        st.markdown(
            f"""
            <div class="section67-alert-error">
                <div class="alert-title">❌ Missing required fields</div>
                <div>
                    The uploaded spreadsheet is missing required columns: <strong><code>{missing_display}</code></strong>.<br/>
                    Per <strong>Spec §51</strong>, all shortlist imports must include these 8 columns:<br/>
                    <code>name, enrollment_number, email, company, drive_id, shortlisted, role, round</code>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Step 5: Preview Parsed Rows (§52)
    # ------------------------------------------------------------------
    if parsed_rows is not None and len(parsed_rows) > 0:
        st.markdown(
            f"""
            <div class="section67-alert-success">
                <div class="alert-title">✅ Spreadsheet Validated ({len(parsed_rows)} Records Found)</div>
                <div>All 8 required columns are present and validated. Review the student records below before confirming import.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="admin-section-header" style="margin-top: 1rem;">3. Preview Records (§52)</div>', unsafe_allow_html=True)
        
        # Summary statistics
        shortlisted_count = sum(
            1 for r in parsed_rows
            if str(r.get("shortlisted", "")).lower() in {"true", "yes", "1", "shortlisted"}
        )
        not_shortlisted_count = len(parsed_rows) - shortlisted_count
        distinct_roles = sorted(list({r.get("role") for r in parsed_rows if r.get("role")}))
        distinct_rounds = sorted(list({r.get("round") for r in parsed_rows if r.get("round")}))

        p_c1, p_c2, p_c3, p_c4 = st.columns(4)
        with p_c1:
            st.metric("Total Candidates", len(parsed_rows))
        with p_c2:
            st.metric("Shortlisted (Yes)", shortlisted_count)
        with p_c3:
            st.metric("Not Shortlisted (No)", not_shortlisted_count)
        with p_c4:
            roles_label = f"{len(distinct_roles)} role(s)" if distinct_roles else "—"
            st.metric("Roles Represented", roles_label)

        # Render preview table
        table_html = """
        <div class="preview-table-wrapper">
            <table class="preview-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Student Name</th>
                        <th>Enrollment No.</th>
                        <th>Email</th>
                        <th>Company</th>
                        <th>Drive ID</th>
                        <th>Shortlisted</th>
                        <th>Role</th>
                        <th>Round</th>
                    </tr>
                </thead>
                <tbody>
        """
        for i, row in enumerate(parsed_rows[:50], start=1):
            is_sl = str(row.get("shortlisted", "")).lower() in {"true", "yes", "1", "shortlisted"}
            sl_badge = '<span class="lifecycle-pill published" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">YES</span>' if is_sl else '<span class="lifecycle-pill expired" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">NO</span>'
            table_html += f"""
                <tr>
                    <td>{i}</td>
                    <td><strong>{row.get('name', '')}</strong></td>
                    <td><code>{row.get('enrollment_number', '')}</code></td>
                    <td>{row.get('email', '')}</td>
                    <td>{row.get('company', '')}</td>
                    <td><code>{row.get('drive_id', '')}</code></td>
                    <td>{sl_badge}</td>
                    <td>{row.get('role', '')}</td>
                    <td>{row.get('round', '')}</td>
                </tr>
            """
        table_html += """
                </tbody>
            </table>
        </div>
        """
        st.markdown(table_html, unsafe_allow_html=True)
        if len(parsed_rows) > 50:
            st.caption(f"Showing first 50 of {len(parsed_rows)} total rows.")

        # --------------------------------------------------------------
        # Step 6: Admin Confirms -> Import (POST /knowledge/import) (§52)
        # --------------------------------------------------------------
        st.markdown('<div class="admin-section-header" style="margin-top: 1.25rem;">4. Coordinator Confirmation (§52)</div>', unsafe_allow_html=True)
        
        st.markdown(
            f"""
            <div class="import-confirm-card">
                <div style="font-size: 0.96rem; font-weight: 700; color: #0F172A; margin-bottom: 0.4rem;">
                    Ready to Persist Shortlist Knowledge Document
                </div>
                <div>• <strong>Placement Drive / Company:</strong> {resolved_company if resolved_company else '<span style="color:#DC2626;">Missing</span>'}</div>
                <div>• <strong>Document Title:</strong> {import_title if import_title else '<span style="color:#DC2626;">Missing</span>'}</div>
                <div>• <strong>Source Reference:</strong> <code>{import_source_ref if import_source_ref else 'Missing'}</code></div>
                <div>• <strong>Version Label:</strong> {import_version_prefix if import_version_prefix else '<span style="color:#DC2626;">Missing</span>'}</div>
                <div>• <strong>Record Count:</strong> {len(parsed_rows)} student candidate records</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_conf_btn, col_conf_space = st.columns([1.5, 2.5])
        with col_conf_btn:
            confirm_import = st.button(
                "🚀 Confirm & Import Shortlist",
                type="primary",
                use_container_width=True,
                help="Persists the validated shortlist to the knowledge base via POST /knowledge/import",
            )

        if confirm_import:
            # Validate required form fields before importing
            metadata_missing = []
            if not resolved_company:
                metadata_missing.append("Placement Drive / Company")
            if not import_title.strip():
                metadata_missing.append("Import Title")
            if not import_source_ref.strip():
                metadata_missing.append("Source Reference")
            if not import_version_prefix.strip():
                metadata_missing.append("Version Prefix")

            if metadata_missing:
                st.markdown(
                    f"""
                    <div class="section67-alert-error">
                        <div class="alert-title">❌ Missing required fields</div>
                        <div>
                            Please provide all required import details before proceeding: <strong>{', '.join(metadata_missing)}</strong>.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif not backend_connected:
                st.error("Cannot complete import: Backend service is currently offline.")
            else:
                import_payload = {
                    "title": import_title.strip(),
                    "source_reference": import_source_ref.strip(),
                    "version_label": import_version_prefix.strip(),
                    "rows": parsed_rows,
                }
                try:
                    with st.spinner("Importing placement shortlist to knowledge base..."):
                        import_resp = import_shortlist(import_payload)
                        doc_id = import_resp.get("document_id", "created")
                        imported_count = import_resp.get("imported", len(parsed_rows))
                        st.success(
                            f"✅ Shortlist successfully imported! {imported_count} records created under Knowledge Document "
                            f"**'{import_title}'** (ID: `{doc_id}`). It is now published and available to students!",
                            icon=":material/check_circle:",
                        )
                        load_knowledge_library.clear()
                        st.rerun()
                except APIClientError:
                    st.error("We couldn't import the shortlist. Please verify the spreadsheet format and try again.", icon=":material/error:")



# ======================================================================
# TAB 3: Knowledge Library & Lifecycle Display (§49, §53)
# ======================================================================
with tab_library:

    st.markdown(
        '<div class="admin-section-header">📚 Policy Lifecycle & Library (Spec §49 & §53)</div>',
        unsafe_allow_html=True,
    )

    # Calculate metrics
    total_count = len(knowledge_docs)
    draft_count = sum(1 for d in knowledge_docs if d.get("status") == "draft")
    published_count = sum(1 for d in knowledge_docs if d.get("status") == "published")
    expired_count = sum(1 for d in knowledge_docs if d.get("status") == "expired")

    # Overview Metrics Row
    m_col1, m_col2, m_col3, m_col4, m_refresh = st.columns([1, 1, 1, 1, 1])
    with m_col1:
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-val">{total_count}</div>
                <div class="summary-lbl">Total Documents</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col2:
        st.markdown(
            f"""
            <div class="summary-card" style="border-top: 3px solid #16A34A;">
                <div class="summary-val" style="color: #166534;">{published_count}</div>
                <div class="summary-lbl">Published (Active)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col3:
        st.markdown(
            f"""
            <div class="summary-card" style="border-top: 3px solid #F59E0B;">
                <div class="summary-val" style="color: #B45309;">{draft_count}</div>
                <div class="summary-lbl">Drafts (Pending)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col4:
        st.markdown(
            f"""
            <div class="summary-card" style="border-top: 3px solid #DC2626;">
                <div class="summary-val" style="color: #991B1B;">{expired_count}</div>
                <div class="summary-lbl">Expired</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_refresh:
        st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Library", use_container_width=True, help="Fetch latest updates from backend"):
            load_knowledge_library.clear()
            st.rerun()

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    # Filter Bar
    f_col1, f_col2, f_col3 = st.columns([1.5, 1.2, 2])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Lifecycle Status",
            options=["All Statuses", "Published", "Draft", "Expired"],
            index=0,
        )
    with f_col2:
        type_options = ["All Types"] + sorted(list({d.get("type", "other") for d in knowledge_docs}))
        type_filter = st.selectbox(
            "Filter by Type",
            options=type_options,
            index=0,
        )
    with f_col3:
        search_query = st.text_input(
            "Search Knowledge",
            placeholder="Search by title, company, or reference...",
        )

    # Filter documents
    filtered_docs = knowledge_docs
    if status_filter != "All Statuses":
        filtered_docs = [d for d in filtered_docs if d.get("status") == status_filter.lower()]
    if type_filter != "All Types":
        filtered_docs = [d for d in filtered_docs if d.get("type") == type_filter]
    if search_query.strip():
        q = search_query.lower().strip()
        filtered_docs = [
            d for d in filtered_docs
            if q in d.get("title", "").lower()
            or q in (d.get("company") or "").lower()
            or q in d.get("source", "").lower()
            or q in str(d.get("content", {})).lower()
        ]

    # Render Documents List
    if not filtered_docs:
        st.markdown(
            f"""
            <div class="empty-state-box">
                <div style="font-size: 1.1rem; font-weight: 600; color: #334155; margin-bottom: 0.4rem;">
                    No knowledge documents match your filter
                </div>
                <div style="font-size: 0.85rem;">
                    {"Create your first policy draft in the 'Create Policy Draft' tab above." if not knowledge_docs else "Try changing the status or search filter."}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        v_col1, v_col2 = st.columns([2.5, 1.5])
        with v_col1:
            st.caption(f"Showing {len(filtered_docs)} knowledge document(s) sourced from GET /knowledge")
        with v_col2:
            view_mode = st.radio(
                "Display Mode",
                options=["📊 Table View (Spec §53)", "🗂️ Cards View (§49)"],
                horizontal=True,
                label_visibility="collapsed",
                key="knowledge_view_mode",
            )

        if view_mode == "📊 Table View (Spec §53)":
            # Knowledge Library Table per Spec §53: Document, Type, Company, Version, Status, Source, Last Updated
            table_html = """
            <div class="knowledge-table-wrapper">
                <table class="knowledge-table">
                    <thead>
                        <tr>
                            <th>Document</th>
                            <th>Type</th>
                            <th>Company</th>
                            <th>Version</th>
                            <th>Status</th>
                            <th>Source</th>
                            <th>Last Updated</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for doc in filtered_docs:
                d_id = doc.get("id")
                d_title = doc.get("title", "Untitled")
                d_type = doc.get("type", "policy")
                d_comp = doc.get("company") or "Institutional"
                d_ver = doc.get("version", "1.0")
                d_status = (doc.get("status") or "draft").lower()
                d_src = doc.get("source", "manual")
                d_created = doc.get("created_at")
                d_time_str = "—"
                if d_created:
                    try:
                        if isinstance(d_created, str):
                            dt = datetime.fromisoformat(d_created.replace("Z", "+00:00"))
                        else:
                            dt = d_created
                        d_time_str = dt.strftime("%b %d, %Y %H:%M")
                    except Exception:
                        d_time_str = str(d_created)

                table_html += f"""
                    <tr>
                        <td>
                            <strong>{d_title}</strong><br/>
                            <span style="font-size: 0.7rem; color: #94A3B8; font-family: monospace;">ID: {d_id}</span>
                        </td>
                        <td><span class="doc-type-pill">{d_type}</span></td>
                        <td>{d_comp}</td>
                        <td><code>{d_ver}</code></td>
                        <td><span class="lifecycle-pill {d_status}">{d_status}</span></td>
                        <td><code>{d_src}</code></td>
                        <td style="white-space: nowrap; font-size: 0.78rem; color: #64748B;">{d_time_str}</td>
                    </tr>
                """
            table_html += """
                    </tbody>
                </table>
            </div>
            """
            st.markdown(table_html, unsafe_allow_html=True)

            # Selected Document Actions & Content Inspector
            st.markdown('<div class="admin-section-header" style="margin-top: 1rem;">⚡ Document Lifecycle Actions & Inspector</div>', unsafe_allow_html=True)
            doc_map = {f"{d.get('title')} [{d.get('status', '').upper()}]": d for d in filtered_docs}
            sel_doc_label = st.selectbox("Select document to inspect or execute lifecycle action:", options=list(doc_map.keys()), key="sel_doc_manage")
            sel_doc = doc_map.get(sel_doc_label)
            if sel_doc:
                s_id = sel_doc.get("id")
                s_status = (sel_doc.get("status") or "draft").lower()
                s_title = sel_doc.get("title")
                s_content = sel_doc.get("content") or {}
                
                act_col1, act_col2, act_space = st.columns([1.2, 1.2, 3])
                with act_col1:
                    if s_status == "draft":
                        if st.button("🚀 Approve & Publish", key=f"t_pub_{s_id}", type="primary", use_container_width=True):
                            try:
                                with st.spinner("Updating policy lifecycle state..."):
                                    patch_knowledge_status(s_id, "published")
                                st.success(f"Published '{s_title}'!")
                                load_knowledge_library.clear()
                                st.rerun()
                            except APIClientError:
                                st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                    elif s_status in {"published", "draft"}:
                        if st.button("🛑 Expire Document", key=f"t_exp_{s_id}", type="primary" if s_status == "published" else "secondary", use_container_width=True):
                            try:
                                with st.spinner("Updating policy lifecycle state..."):
                                    patch_knowledge_status(s_id, "expired")
                                st.warning(f"Expired '{s_title}'")
                                load_knowledge_library.clear()
                                st.rerun()
                            except APIClientError:
                                st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                    elif s_status == "expired":
                        if st.button("♻️ Re-activate", key=f"t_act_{s_id}", type="primary", use_container_width=True):
                            try:
                                with st.spinner("Updating policy lifecycle state..."):
                                    patch_knowledge_status(s_id, "published")
                                st.success(f"Re-activated '{s_title}'!")
                                load_knowledge_library.clear()
                                st.rerun()
                            except APIClientError:
                                st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                with act_col2:
                    if s_status != "draft":
                        if st.button("↩️ Revert to Draft", key=f"t_dft_{s_id}", use_container_width=True):
                            try:
                                with st.spinner("Updating policy lifecycle state..."):
                                    patch_knowledge_status(s_id, "draft")
                                st.info(f"Reverted '{s_title}' to Draft")
                                load_knowledge_library.clear()
                                st.rerun()
                            except APIClientError:
                                st.error("We couldn't update the document status. Please try again.", icon=":material/error:")

                with st.expander(f"🔎 Content Parameters for '{s_title}'", expanded=False):
                    st.json(s_content)


        else:
            # Cards & Inspector View (§49)
            for doc in filtered_docs:
                doc_id = doc.get("id")
                doc_title = doc.get("title", "Untitled Document")
                doc_type = doc.get("type", "policy")
                doc_company = doc.get("company") or "Institutional / General"
                doc_version = doc.get("version", "1.0")
                doc_status = (doc.get("status") or "draft").lower()
                doc_source = doc.get("source", "manual")
                doc_content = doc.get("content") or {}
                created_at = doc.get("created_at")
                
                created_label = ""
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            dt = created_at
                        created_label = dt.strftime("%b %d, %Y %H:%M")
                    except Exception:
                        created_label = str(created_at)

                card_class = f"knowledge-card {doc_status}-card"
                pill_class = f"lifecycle-pill {doc_status}"

                # Render Card Container
                with st.container():
                    st.markdown(
                        f"""
                        <div class="{card_class}">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.35rem;">
                                <div>
                                    <span class="{pill_class}">{doc_status}</span>
                                    <span class="doc-type-pill" style="margin-left: 0.4rem;">{doc_type}</span>
                                </div>
                                <span style="font-size: 0.72rem; color: #94A3B8; font-family: monospace;">ID: {doc_id}</span>
                            </div>
                            <div class="knowledge-title">{doc_title}</div>
                            <div class="knowledge-meta">
                                <span>🏢 <strong>Company:</strong> {doc_company}</span>
                                <span>🏷️ <strong>Version:</strong> {doc_version}</span>
                                <span>🔗 <strong>Source:</strong> <code>{doc_source}</code></span>
                                {f'<span>🕒 <strong>Created:</strong> {created_label}</span>' if created_label else ''}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Content Details Accordion & Lifecycle Actions
                    col_details, col_actions = st.columns([3.2, 1.8])
                    
                    with col_details:
                        with st.expander("🔎 View Content Details & Policy Parameters", expanded=False):
                            if isinstance(doc_content, dict) and doc_content:
                                # Render structured fields if present
                                elig = doc_content.get("eligibility")
                                ctc = doc_content.get("salary_ctc")
                                dl = doc_content.get("deadline")
                                app_url = doc_content.get("application_url")
                                instr = doc_content.get("instructions")
                                res = doc_content.get("resolution")
                                rec_count = doc_content.get("record_count")

                                if any([elig, ctc, dl, app_url, instr]):
                                    grid_html = "<div class='knowledge-content-grid'>"
                                    if elig:
                                        grid_html += f"<div class='knowledge-content-field'><div class='knowledge-content-field-label'>Eligibility</div><div>{elig}</div></div>"
                                    if ctc:
                                        grid_html += f"<div class='knowledge-content-field'><div class='knowledge-content-field-label'>Salary / CTC</div><div>{ctc}</div></div>"
                                    if dl:
                                        grid_html += f"<div class='knowledge-content-field'><div class='knowledge-content-field-label'>Deadline</div><div>{dl}</div></div>"
                                    if app_url:
                                        grid_html += f"<div class='knowledge-content-field'><div class='knowledge-content-field-label'>Application URL</div><div><a href='{app_url}' target='_blank' style='color:#2563EB;'>{app_url}</a></div></div>"
                                    grid_html += "</div>"
                                    st.markdown(grid_html, unsafe_allow_html=True)

                                if instr:
                                    st.markdown(
                                        f"<div class='knowledge-content-field-label' style='margin-top:0.4rem;'>Instructions</div><div style='font-size:0.83rem;'>{instr}</div>",
                                        unsafe_allow_html=True,
                                    )
                                elif res:
                                    st.markdown(
                                        f"<div class='knowledge-content-field-label'>Resolution</div><div style='font-size:0.83rem;'>{res}</div>",
                                        unsafe_allow_html=True,
                                    )
                                elif rec_count:
                                    st.markdown(
                                        f"<div class='knowledge-content-field-label'>Shortlist Records</div><div style='font-size:0.83rem;'>{rec_count} students shortlisted</div>",
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.json(doc_content)
                            else:
                                st.caption("No custom content payload associated with this document.")

                    with col_actions:
                        # Policy Lifecycle Actions per §49
                        btn_row1, btn_row2 = st.columns(2)
                        
                        # If Draft -> can Approve/Publish or Expire
                        if doc_status == "draft":
                            with btn_row1:
                                if st.button(
                                    "🚀 Approve",
                                    key=f"pub_{doc_id}",
                                    help="Approve and make visible to student AI guidance",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "published")
                                        st.success(f"Published '{doc_title}'!")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                            with btn_row2:
                                if st.button(
                                    "🛑 Expire",
                                    key=f"exp_{doc_id}",
                                    help="Mark as expired immediately",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "expired")
                                        st.warning(f"Expired '{doc_title}'")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")

                        # If Published -> can Expire or Revert to Draft
                        elif doc_status == "published":
                            with btn_row1:
                                if st.button(
                                    "🛑 Expire",
                                    key=f"exp_{doc_id}",
                                    type="primary",
                                    help="Expire this policy so AI stops providing it to students (§54)",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "expired")
                                        st.warning(f"Marked '{doc_title}' as Expired")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                            with btn_row2:
                                if st.button(
                                    "↩️ Draft",
                                    key=f"dft_{doc_id}",
                                    help="Revert to Draft for editing",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "draft")
                                        st.info(f"Reverted '{doc_title}' to Draft")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")

                        # If Expired -> can Re-activate (Publish) or Re-draft
                        elif doc_status == "expired":
                            with btn_row1:
                                if st.button(
                                    "♻️ Re-activate",
                                    key=f"pub_{doc_id}",
                                    help="Re-publish this expired knowledge document",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "published")
                                        st.success(f"Re-activated '{doc_title}'!")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")
                            with btn_row2:
                                if st.button(
                                    "↩️ Draft",
                                    key=f"dft_{doc_id}",
                                    help="Set back to Draft for revisions",
                                    use_container_width=True,
                                ):
                                    try:
                                        with st.spinner("Updating policy lifecycle state..."):
                                            patch_knowledge_status(doc_id, "draft")
                                        st.info(f"Set '{doc_title}' to Draft")
                                        load_knowledge_library.clear()
                                        st.rerun()
                                    except APIClientError:
                                        st.error("We couldn't update the document status. Please try again.", icon=":material/error:")


                    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
