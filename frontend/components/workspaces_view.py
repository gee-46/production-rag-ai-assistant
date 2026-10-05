"""
Workspace Management & RBAC Administration Component.
"""
from __future__ import annotations

import streamlit as st
from frontend.api_client import APIClient


def render_workspaces_view(
    client: APIClient,
    active_workspace: dict | None = None,
    workspace_id: str | None = None,
):
    if active_workspace is None:
        active_workspace = {"id": workspace_id or "default", "name": "Production Knowledge Base"}
    elif isinstance(active_workspace, str):
        active_workspace = {"id": active_workspace, "name": "Production Knowledge Base"}

    ws_id = str(active_workspace.get("id") or workspace_id or "default")
    ws_name = active_workspace.get("name", "Production Knowledge Base")

    st.markdown("### ⚙️ Administration")
    st.caption("Manage workspaces and access permissions.")

    # 1. Workspace Section
    col_ws_select, col_ws_create = st.columns([3, 2])

    with col_ws_select:
        st.markdown("#### 📁 Workspace")
        workspaces = client.list_workspaces()
        st.session_state["workspaces"] = workspaces

        if workspaces:
            current_idx = 0
            for i, w in enumerate(workspaces):
                if w.get("id") == ws_id:
                    current_idx = i
                    break

            selected_idx = st.selectbox(
                "Active Workspace",
                range(len(workspaces)),
                index=current_idx,
                format_func=lambda i: f"📁 {workspaces[i].get('name')}",
                label_visibility="collapsed",
            )

            if selected_idx != current_idx:
                st.session_state["active_workspace"] = workspaces[selected_idx]
                st.session_state["messages"] = []
                st.session_state["session_id"] = None
                st.rerun()

            curr_ws = workspaces[selected_idx]
            st.markdown(
                f"""
                <div class="kpi-card" style="margin-top: 0.5rem; padding: 0.75rem 1rem;">
                    <div class="kpi-label">Current Workspace</div>
                    <div class="kpi-value" style="font-size: 1.15rem;">{curr_ws.get('name')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No workspaces available. Create one to get started.")

    with col_ws_create:
        with st.expander("➕ Create New Workspace", expanded=False):
            with st.form("create_workspace_form"):
                new_name = st.text_input("Workspace Name", placeholder="e.g. Legal & Compliance Knowledge Base")
                submitted = st.form_submit_button("Create Workspace", type="primary", use_container_width=True)
                if submitted:
                    if not new_name.strip():
                        st.error("Please enter a workspace name.")
                    else:
                        with st.spinner("Creating workspace..."):
                            res = client.create_workspace(new_name.strip())
                            if res.get("success"):
                                st.success(f"Workspace '{new_name}' created!")
                                st.session_state["workspaces"] = client.list_workspaces()
                                st.session_state["active_workspace"] = res.get("data")
                                st.rerun()
                            else:
                                st.error(f"Error: {res.get('error')}")

    st.markdown("<hr style='margin: 1.25rem 0; opacity: 0.1;'/>", unsafe_allow_html=True)

    # 2. Members & Access Control Section
    st.markdown(f"#### 👥 Members — {ws_name}")

    # Members Table
    members_data = [
        {"User": "Workspace Administrator", "Email": "admin@enterprise.local", "Role": "Admin"},
        {"User": "Workspace Operator", "Email": "operator@workspace.local", "Role": "Member"},
    ]

    col_m1, col_m2 = st.columns([3, 2])

    with col_m1:
        st.markdown(
            """
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 0.5rem 0.75rem;">
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 0.4rem 0.25rem; font-size: 0.75rem; color: #94A3B8; font-weight: 600;">
                    <span>USER</span>
                    <span>ROLE</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.25rem; border-bottom: 1px solid rgba(255,255,255,0.04);">
                    <div>
                        <div style="font-weight: 600; font-size: 0.82rem; color: #F1F5F9;">Workspace Administrator</div>
                        <div style="font-size: 0.72rem; color: #64748B;">admin@enterprise.local</div>
                    </div>
                    <span class="badge badge-green">Owner / Admin</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.25rem;">
                    <div>
                        <div style="font-weight: 600; font-size: 0.82rem; color: #F1F5F9;">Workspace Operator</div>
                        <div style="font-size: 0.72rem; color: #64748B;">operator@workspace.local</div>
                    </div>
                    <span class="badge badge-blue">Member</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_m2:
        with st.container():
            st.markdown("##### ✉️ Invite Member")
            invite_email = st.text_input("User Email", placeholder="colleague@company.com", key="invite_email_input")
            invite_role = st.selectbox(
                "Access Role",
                ["Member", "Viewer", "Admin"],
                help="Admin: full manage access; Member: upload and chat; Viewer: chat only.",
                key="invite_role_select",
            )
            if st.button("📨 Grant Access", type="primary", use_container_width=True, key="grant_access_btn"):
                if not invite_email.strip():
                    st.error("Please enter an email address.")
                else:
                    with st.spinner("Granting workspace permissions..."):
                        inv_res = client.invite_member(
                            workspace_id=ws_id,
                            email=invite_email.strip(),
                            role=invite_role.lower(),
                        )
                        if inv_res.get("success"):
                            st.success(f"✓ {invite_email.strip()} added with role '{invite_role}'")
                        else:
                            st.error(f"Error: {inv_res.get('error')}")

