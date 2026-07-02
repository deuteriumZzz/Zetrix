from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

def _load_sources():
    """Active sources, read from the Django API (DB-driven) rather than a
    hand-authored YAML file — adding a country's scraping source is now a
    Django admin/API action, not a DAG redeploy. See utils/api_client.py.
    """
    from utils.api_client import DjangoAPIClient
    return DjangoAPIClient().get_sources()

def _scrape(source_id, **ctx):
    from utils.api_client import DjangoAPIClient
    result = DjangoAPIClient().trigger_scrape(source_id)
    ctx["ti"].xcom_push(key="task_id", value=result.get("task_id"))
    return result

def _compute_aggregates(**ctx):
    import httpx, os, logging
    url = f"{os.getenv('DJANGO_API_URL','http://web:8000/api/v1')}/prices/aggregates/compute/"
    try:
        httpx.post(url, json={"date": ctx["ds"]},
                   headers={"Authorization": f"Token {os.getenv('DJANGO_API_TOKEN','dev-token')}"},
                   timeout=60).raise_for_status()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Aggregate compute: {e}")

def _generate_daily_report(country_id, region_id, region_label, market_type, **ctx):
    from utils.api_client import DjangoAPIClient
    d = ctx["ds"]
    report = DjangoAPIClient().trigger_report({
        "title": f"Daily — {region_label}/{market_type} ({d})",
        "country": country_id, "region": region_id, "market_type": market_type,
        "date_from": d, "date_to": d, "format": "pdf",
    })
    ctx["ti"].xcom_push(key="report_pk", value=report.get("id"))
    return report

def _send_telegram(group_id, **ctx):
    pk = ctx["ti"].xcom_pull(task_ids=f"{group_id}.generate_report", key="report_pk")
    if pk:
        from utils.api_client import DjangoAPIClient
        DjangoAPIClient().send_report_telegram(pk)

DEFAULT_ARGS = {"owner": "bali_market", "retries": 2,
                "retry_delay": timedelta(minutes=5), "email_on_failure": False}

with DAG(dag_id="bali_market_analyzer",
         description="Daily scraping and reporting across all active sources",
         schedule="0 8 * * *",
         start_date=datetime(2024, 1, 1),
         catchup=False, default_args=DEFAULT_ARGS,
         tags=["global", "market", "scraping"]) as dag:

    for source in _load_sources():
        if not source.get("is_active", True):
            continue
        name = source["name"]
        country_id = source["country"]
        region_id = source.get("region")
        region_label = source.get("region_name") or source.get("country_name") or name
        mtype = source["market_type"]
        gid = f"source_{name}"
        with TaskGroup(group_id=gid):
            t1 = PythonOperator(task_id="scrape", python_callable=_scrape, op_kwargs={"source_id": source["id"]})
            t2 = PythonOperator(task_id="compute_aggregates", python_callable=_compute_aggregates)
            t3 = PythonOperator(task_id="generate_report", python_callable=_generate_daily_report,
                                op_kwargs={
                                    "country_id": country_id, "region_id": region_id,
                                    "region_label": region_label, "market_type": mtype,
                                })
            t4 = PythonOperator(task_id="send_telegram", python_callable=_send_telegram, op_kwargs={"group_id": gid})
            t1 >> t2 >> t3 >> t4
