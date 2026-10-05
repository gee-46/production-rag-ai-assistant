"""
Real-time System Observability & Prometheus Metrics Inspector Component.
"""
from __future__ import annotations

import re
import streamlit as st
from frontend.api_client import APIClient


def parse_prometheus_metrics(raw_text: str) -> dict:
    parsed: dict[str, list[dict]] = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+([0-9.eE+-]+)", line)
        if match:
            metric_name, labels_str, val_str = match.groups()
            try:
                val = float(val_str)
            except ValueError:
                val = val_str

            labels = {}
            if labels_str:
                for pair in labels_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k.strip()] = v.strip().strip('"')

            if metric_name not in parsed:
                parsed[metric_name] = []
            parsed[metric_name].append({"labels": labels, "value": val})
    return parsed


def render_metrics_view(client: APIClient):
    st.markdown("### 📈 Observability & Prometheus Telemetry")
    st.caption("Inspect live service health, request throughput, retrieval latencies, and generation histograms.")

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        health_info = client.check_health()
        if health_info.get("status") == "ok":
            st.success(f"✅ Backend Health: Healthy (`{client.base_url}`)")
            st.json(health_info.get("data", {}))
        else:
            st.error(f"❌ Backend Offline: {health_info.get('error')}")

    with col_h2:
        if st.button("🔄 Scrape Live Metrics", use_container_width=True):
            st.rerun()

    st.markdown("---")

    metrics_res = client.get_metrics()
    if metrics_res.get("status") == "ok":
        raw_text = metrics_res.get("raw_text", "")
        parsed = parse_prometheus_metrics(raw_text)

        st.markdown("#### ⚡ Real-Time Pipeline Metrics")

        # Extract HTTP Requests Total
        http_requests = parsed.get("http_requests_total", [])
        total_requests = sum(item["value"] for item in http_requests if isinstance(item["value"], (int, float)))

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("🌐 Total HTTP Requests", int(total_requests))

        # Check retrieval & generation metrics
        retrieval_metrics = parsed.get("rag_retrieval_duration_seconds_count", [])
        generation_metrics = parsed.get("rag_generation_duration_seconds_count", [])

        with m2:
            retrieval_count = sum(item["value"] for item in retrieval_metrics if isinstance(item["value"], (int, float)))
            st.metric("🔍 Hybrid Search Queries", int(retrieval_count))

        with m3:
            gen_count = sum(item["value"] for item in generation_metrics if isinstance(item["value"], (int, float)))
            st.metric("⚡ LLM Generations", int(gen_count))

        # Prometheus Breakdown Table
        with st.expander("📊 HTTP Status Code Breakdown", expanded=True):
            if http_requests:
                breakdown_data = []
                for item in http_requests:
                    lbls = item.get("labels", {})
                    breakdown_data.append({
                        "Method": lbls.get("method", "—"),
                        "Route / Path": lbls.get("path", "—"),
                        "Status Code": lbls.get("status_code", "—"),
                        "Count": item.get("value", 0),
                    })
                st.dataframe(breakdown_data, use_container_width=True)

        with st.expander("📜 Raw Prometheus Exposition (/metrics)", expanded=False):
            st.code(raw_text, language="text")
    else:
        st.warning(f"Could not scrape metrics from `{client.base_url}/metrics`: {metrics_res.get('error')}")
