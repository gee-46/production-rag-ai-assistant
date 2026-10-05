"""
Authentication component for User Login and Registration.
"""
from __future__ import annotations

import streamlit as st
from frontend.api_client import APIClient


def render_auth_view(client: APIClient):
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="margin-bottom: 0.25rem;">🔐 Access RAG Assistant</h2>
            <p style="color: #94A3B8;">Sign in to query indexed enterprise knowledge bases, upload files, or run evals.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔑 Sign In", "✨ Create Account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email Address", value=st.session_state.get("auth_email_prefill", "lead.engineer@company.com"))
                password = st.text_input("Password", type="password", value="SecurePassword123!")
                submit_login = st.form_submit_button("Sign In to Platform", type="primary", use_container_width=True)

                if submit_login:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Authenticating..."):
                            res = client.login(email.strip(), password)
                            if res.get("success"):
                                token = res.get("token")
                                st.session_state["token"] = token
                                st.session_state["user_email"] = email.strip()
                                client.set_token(token)

                                # Load workspaces
                                workspaces = client.list_workspaces()
                                st.session_state["workspaces"] = workspaces
                                if workspaces:
                                    st.session_state["active_workspace"] = workspaces[0]
                                else:
                                    # Create default workspace if none
                                    ws_res = client.create_workspace("Knowledge Base")
                                    if ws_res.get("success"):
                                        st.session_state["workspaces"] = [ws_res["data"]]
                                        st.session_state["active_workspace"] = ws_res["data"]

                                st.success("Authentication successful! Welcome back.")
                                st.rerun()
                            else:
                                st.error(f"Sign In failed: {res.get('error')}")

            # Quick Demo helper
            st.markdown("---")
            st.caption("💡 **Demo Quick Start:** If running for the first time, switch to the 'Create Account' tab to create `lead.engineer@company.com` or any email, then sign in.")

        with tab_register:
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", value="Lead Engineer")
                reg_email = st.text_input("Email Address", value="lead.engineer@company.com")
                reg_pass = st.text_input("Password (min 8 chars)", type="password", value="SecurePassword123!")
                submit_reg = st.form_submit_button("Create New Account", type="primary", use_container_width=True)

                if submit_reg:
                    if not reg_email or not reg_pass:
                        st.error("Email and password are required.")
                    elif len(reg_pass) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        with st.spinner("Registering user..."):
                            res = client.register(reg_email.strip(), reg_pass, reg_name.strip() if reg_name else None)
                            if res.get("success"):
                                st.success("Account created successfully! Logging you in...")
                                # Auto login
                                login_res = client.login(reg_email.strip(), reg_pass)
                                if login_res.get("success"):
                                    token = login_res.get("token")
                                    st.session_state["token"] = token
                                    st.session_state["user_email"] = reg_email.strip()
                                    client.set_token(token)
                                    ws_res = client.create_workspace("Production Architecture Workspace")
                                    if ws_res.get("success"):
                                        st.session_state["workspaces"] = [ws_res["data"]]
                                        st.session_state["active_workspace"] = ws_res["data"]
                                    st.rerun()
                                else:
                                    st.info("Please switch to the Sign In tab to enter your credentials.")
                            else:
                                st.error(f"Registration failed: {res.get('error')}")
