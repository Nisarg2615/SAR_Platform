import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from ui import api_client, mock_data

st.set_page_config(page_title="SAR Platform", layout="wide")

st.sidebar.title("SAR Platform 🕵️")
page = st.sidebar.radio("Navigation", ["Dashboard", "Submit Transaction", "Risk Analysis", "Graph View", "SAR Review", "Audit Trail"])

# Check API Health
health = api_client.check_health()
if health:
    st.sidebar.success("Backend: ONLINE")
    USE_MOCK = False
else:
    st.sidebar.warning("Backend offline — showing mock data")
    USE_MOCK = True


def get_all_cases():
    if USE_MOCK:
        return [mock_data.mock_case_structuring.model_dump()]
    cases = api_client.get_cases() or []
    if not cases:
        return [mock_data.mock_case_structuring.model_dump()]
    return cases


def get_case(c_id: str):
    if USE_MOCK:
        return mock_data.mock_case_structuring.model_dump()
    case = api_client.get_case(c_id)
    return case if case else mock_data.mock_case_structuring.model_dump()


case_id = st.sidebar.text_input("Active Case ID", "CASE-MOCK-101")

if page == "Dashboard":
    st.title("📊 Dashboard - All Cases")
    all_cases = get_all_cases()
    
    if not all_cases:
        st.info("No cases found. Submit a transaction to get started.")
    else:
        st.write(f"**Total Cases:** {len(all_cases)}")
        
        col1, col2, col3, col4 = st.columns(4)
        status_counts: dict = {}
        for c in all_cases:
            status = c.get("status", "PENDING")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        with col1:
            st.metric("Total", len(all_cases))
        with col2:
            st.metric("Pending", status_counts.get("pending", 0))
        with col3:
            st.metric("In Review", status_counts.get("in_review", 0))
        with col4:
            st.metric("Filed", status_counts.get("filed", 0))
        
        st.subheader("📋 All Cases")
        case_data = []
        for c in all_cases:
            case_data.append({
                "Case ID": c.get("case_id", "N/A"),
                "Status": c.get("status", "PENDING"),
                "Risk Tier": c.get("risk_tier", "PENDING"),
                "Subject": c.get("subject", c.get("normalized", {}).get("subject_name", "Unknown")),
                "Last Updated": c.get("last_updated", "N/A")
            })
        
        if case_data:
            df = pd.DataFrame(case_data)
            st.dataframe(df, use_container_width=True)
            
            selected_case = st.selectbox("Select a case to view details", [c.get("case_id") for c in all_cases])
            if selected_case:
                st.session_state["selected_case_id"] = selected_case
        
        if "selected_case_id" in st.session_state:
            st.markdown("---")
            st.subheader(f"📄 Case Details: {st.session_state['selected_case_id']}")
            selected = get_case(st.session_state["selected_case_id"])
            
            if selected.get("normalized"):
                norm = selected["normalized"]
                st.write(f"**Subject:** {norm.get('subject_name', 'N/A')}")
                st.write(f"**Total Amount:** ${norm.get('total_amount_usd', 0):,.2f}")
                st.write(f"**Date Range:** {norm.get('date_range_start', 'N/A')} to {norm.get('date_range_end', 'N/A')}")
            
            if selected.get("risk_assessment"):
                risk = selected["risk_assessment"]
                st.write(f"**Risk Score:** {risk.get('risk_score', 'N/A')} | **Tier:** {risk.get('risk_tier', 'N/A')}")
                st.write(f"**Typology:** {risk.get('matched_typology', 'N/A')}")
            
            if selected.get("compliance"):
                comp = selected["compliance"]
                st.write(f"**BSA Compliant:** {'Yes' if comp.get('bsa_compliant') else 'No'}")

elif page == "Submit Transaction":
    st.title("💸 Submit Transaction")
    if not USE_MOCK:
        all_cases = api_client.get_cases()
        if all_cases:
            case_list = [c.get("case_id", "N/A") for c in all_cases]
            if case_list:
                case_id = st.sidebar.selectbox("Select Case", case_list, index=len(case_list)-1)
    
    col1, col2, col3 = st.columns(3)
    if col1.button("Simulate Structuring"):
        res = api_client.simulate_scenario("structuring")
        if res: st.success(f"Case {res['case_id']} created!")
    if col2.button("Simulate Layering"):
        res = api_client.simulate_scenario("layering")
        if res: st.success(f"Case {res['case_id']} created!")
    if col3.button("Simulate Smurfing"):
        res = api_client.simulate_scenario("smurfing")
        if res: st.success(f"Case {res['case_id']} created!")
        
    with st.form("tx_form"):
        st.write("Manual Entry")
        amt = st.number_input("Amount (USD)", 0.0, 100000.0, 5000.0)
        ttype = st.selectbox("Type", ["wire", "ach", "cash"])
        geo = st.text_input("Geography", "domestic")
        acc = st.text_input("Account ID", "ACC001")
        if st.form_submit_button("Submit"):
            payload = {"amount_usd": amt, "transaction_type": ttype, "geography": geo, "account_id": acc}
            if not USE_MOCK:
                created = api_client.submit_transaction(payload)
                if created: st.success(f"Case {created['case_id']} created!")
            else:
                st.info("Mock Mode: Transaction recorded locally.")

elif page == "Risk Analysis":
    st.title("⚖️ Risk Analysis")
    case = get_case(case_id)
    if case.get("risk_assessment"):
        risk = case["risk_assessment"]
        st.metric("Risk Score", value=risk["risk_score"])
        st.warning(f"Tier: {risk['risk_tier']}")
        st.info(f"Typology: {risk['matched_typology']}")
        if risk.get("shap_values"):
            df = pd.DataFrame.from_dict(risk["shap_values"], orient="index", columns=["Importance"])
            st.bar_chart(df)
    else:
        st.info("Case pending risk assessment.")

elif page == "Graph View":
    st.title("🕸️ Graph View")
    st.write("Graph visualization placeholder")
    if not USE_MOCK:
        graph_data = api_client.get_graph(case_id)
        if graph_data:
            st.json(graph_data)

elif page == "SAR Review":
    st.title("📄 SAR Review — FIU-IND STR")
    case = get_case(case_id)
    
    if case.get("narrative"):
        narr = case["narrative"]
        
        st.subheader("📋 Part 1: Report Details")
        p1 = narr.get("part1_report_details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"📅 **Date of Sending:** {p1.get('date_of_sending', 'N/A')}")
        with col2:
            st.write(f"🔄 **Replacement Report:** {'Yes' if p1.get('is_replacement') else 'No'}")
        with col3:
            st.write(f"📆 **Original Report Date:** {p1.get('date_of_original_report', 'N/A')}")
        
        st.divider()
        st.subheader("👤 Part 2: Principal Officer")
        p2 = narr.get("part2_principal_officer", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"🏦 **Bank Name:** {p2.get('bank_name', 'N/A')}")
            st.write(f"🔢 **BSR Code:** {p2.get('bsr_code', 'N/A')}")
            st.write(f"🆔 **FIU ID:** {p2.get('fiu_id', 'N/A')}")
        with col2:
            st.write(f"📂 **Bank Category:** {p2.get('bank_category', 'N/A')}")
            st.write(f"👤 **Officer Name:** {p2.get('officer_name', 'N/A')}")
            st.write(f"💼 **Designation:** {p2.get('designation', 'N/A')}")
        with col3:
            st.write(f"📍 **Address:** {p2.get('address', 'N/A')}")
            st.write(f"🌍 **City/District:** {p2.get('city_town_district', 'N/A')}")
            st.write(f"🗺️ **State/Country:** {p2.get('state_country', 'N/A')}")
        
        st.divider()
        st.subheader("🏢 Part 3: Reporting Branch")
        p3 = narr.get("part3_reporting_branch", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"🏢 **Branch Name:** {p3.get('branch_name', 'N/A')}")
            st.write(f"🔢 **BSR Code:** {p3.get('bsr_code', 'N/A')}")
        with col2:
            st.write(f"🆔 **FIU ID:** {p3.get('fiu_id', 'N/A')}")
            st.write(f"📍 **Address:** {p3.get('address', 'N/A')}")
        with col3:
            st.write(f"🌍 **City/District:** {p3.get('city_town_district', 'N/A')}")
            st.write(f"🗺️ **State/Country:** {p3.get('state_country', 'N/A')}")
        
        st.divider()
        st.subheader("👥 Part 4: Linked Individuals")
        p4 = narr.get("part4_linked_individuals", [])
        if p4:
            for i, ind in enumerate(p4):
                st.write(f"**{i+1}.** {ind.get('name', 'N/A')} (ID: {ind.get('customer_id', 'N/A')})")
        else:
            st.write("None")
        
        st.subheader("🏛️ Part 5: Linked Entities")
        p5 = narr.get("part5_linked_entities", [])
        if p5:
            for i, ent in enumerate(p5):
                st.write(f"**{i+1}.** {ent.get('name', 'N/A')} (ID: {ent.get('customer_id', 'N/A')})")
        else:
            st.write("None")
        
        st.subheader("💳 Part 6: Linked Accounts")
        p6 = narr.get("part6_linked_accounts", [])
        if p6:
            for i, acc in enumerate(p6):
                st.write(f"**{i+1}.** {acc.get('account_number', 'N/A')} - {acc.get('account_holder_name', 'N/A')}")
        else:
            st.write("None")
        
        st.divider()
        st.subheader("🚨 Part 7: Suspicion Details")
        p7 = narr.get("part7_suspicion_details", {})
        rs = p7.get("reasons_for_suspicion", [])
        st.write("**🚩 Reasons for Suspicion:**")
        if rs:
            for reason in rs:
                st.write(f"  • {reason}")
        else:
            st.write("None")
        st.text_area("Grounds of Suspicion (Narrative Sequence)", p7.get('grounds_of_suspicion', ''), height=300, key="p7_grounds")
        
        st.divider()
        st.subheader("⚖️ Part 8: Action Taken")
        p8 = narr.get("part8_action_taken", {})
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"🔍 **Under Investigation:** {'Yes' if p8.get('under_investigation') else 'No'}")
        with col2:
            st.write(f"🏢 **Agency Details:** {p8.get('agency_details', 'None')}")
        
        st.divider()
        st.caption(f"📝 Generated: {narr.get('generation_timestamp', 'N/A')}")
    
    if case.get("compliance"):
        comp = case["compliance"]
        st.write("### Compliance Checklist")
        if not comp.get("compliance_issues"):
            st.write("✅ All checks passed")
        else:
            for issue in comp["compliance_issues"]: st.write(f"❌ {issue}")
            
    analyst = st.text_input("Analyst Name", "Analyst-1")
    col1, col2 = st.columns(2)
    if col1.button("Approve and File"):
        if not USE_MOCK: api_client.approve_case(case_id, analyst)
        st.balloons()
        st.success("Case FILED")
    if col2.button("Dismiss"):
        if not USE_MOCK: api_client.dismiss_case(case_id)
        st.success("Case DISMISSED")

elif page == "Audit Trail":
    st.title("📜 Audit Trail")
    case = get_case(case_id)
    if case.get("audit_trail"):
        for entry in case["audit_trail"]:
            with st.expander(entry.get("agent", "System")):
                st.write(f"**Action:** {entry.get('action')}")
                st.write(f"**Confidence:** {entry.get('confidence')}")
                st.write(f"**Timestamp:** {entry.get('timestamp')}")
    
    if case.get("audit") and case["audit"].get("immutable_hash"):
        st.code(case["audit"]["immutable_hash"], language="text")
        st.caption("Immutable — cannot be modified")

    import requests
    try:
        res = requests.get("http://127.0.0.1:8000/health", timeout=3)
        if res.status_code == 200:
            hdata = res.json()
            orch = hdata.get("orchestrator")
            if orch:
                with st.expander("🔀 LLM Provider Routing", expanded=False):
                    routing = orch.get("agent_routing", {})
                    health_status = orch.get("provider_health", {})
                    
                    routing_data = []
                    for ag, val in routing.items():
                        provider = val.split(":")[0] if ":" in val else "unknown"
                        model = val.split(":")[1] if ":" in val else "unknown"
                        is_healthy = health_status.get(provider, False)
                        status_str = "🟢 Active" if is_healthy else "🔴 Offline/Fallback"
                        routing_data.append({"Agent": ag, "Provider": provider, "Model": model, "Health": status_str})
                    
                    if routing_data:
                        st.table(routing_data)
    except Exception:
        pass
