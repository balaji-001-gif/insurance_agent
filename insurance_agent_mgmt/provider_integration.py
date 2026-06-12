# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Provider Integration Engine
---------------------------
Generic framework for integrating with external insurance provider APIs
(e.g., LIC India, HDFC Life, ICICI Prudential, etc.).

Architecture:
  BaseProviderClient (abstract)
    └── LICClient (concrete example)
  
  sync_all_providers()          — scheduled task entry point
  sync_provider_integration()   — orchestrate one integration
"""

import json
import frappe
from frappe.utils import today, now_datetime, add_days


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_active_integrations():
    """Return all active Provider API Integrations."""
    return frappe.db.get_all(
        "Provider API Integration",
        filters={"is_active": 1, "sync_enabled": 1},
        fields=["name", "provider_name", "api_base_url", "auth_method",
                "sync_interval_minutes", "last_sync_start", "last_sync_end",
                "sync_plans", "sync_customers", "sync_policies",
                "sync_renewals", "push_claims", "push_policy_updates"],
    )


def _get_integration_doc(name):
    """Load full integration document."""
    return frappe.get_doc("Provider API Integration", name)


def _get_client_for_integration(integration):
    """Factory: return the appropriate client class for a provider."""
    provider_name = (integration.provider_name or "").strip().lower()

    # Map known providers to their client classes
    if "lic" in provider_name:
        return LICClient(integration)
    if "hdfc" in provider_name:
        return HDFCLifeClient(integration)

    # Fallback to generic REST client
    return GenericProviderClient(integration)


# ──────────────────────────────────────────────
# Base Client
# ──────────────────────────────────────────────

class BaseProviderClient:
    """Base class for provider-specific API clients.
    
    Subclasses MUST override at least fetch_plans().
    Other methods default to returning empty lists / False.
    """

    def __init__(self, integration):
        self.integration = integration
        self.base_url = integration.api_base_url.rstrip("/")
        self._session = None

    # ── HTTP layer ─────────────────────────────

    def _get_headers(self):
        """Build auth + content-type headers based on integration config."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        creds = self.integration.get_decrypted_credentials()
        method = (self.integration.auth_method or "").strip()

        if method == "API Key":
            headers["X-API-Key"] = creds["api_key"] or ""
        elif method == "Basic Auth":
            import base64
            token = base64.b64encode(
                f"{creds['api_key'] or ''}:{creds['api_secret'] or ''}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {token}"
        elif method == "Bearer Token":
            headers["Authorization"] = f"Bearer {creds['access_token'] or creds['api_key'] or ''}"
        elif method == "OAuth2":
            headers["Authorization"] = f"Bearer {creds['access_token'] or ''}"

        # Merge additional static headers from integration config
        if self.integration.additional_headers:
            try:
                extra = json.loads(self.integration.additional_headers)
                headers.update(extra)
            except (json.JSONDecodeError, TypeError):
                pass

        return headers

    def _request(self, method, endpoint, **kwargs):
        """Make an HTTP request and return parsed JSON response or None."""
        import requests

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                timeout=kwargs.pop("timeout", 30),
                **kwargs,
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"status": "ok"}
        except requests.exceptions.Timeout:
            frappe.log_error(
                title="Provider API Timeout",
                message=f"Timeout calling {method.upper()} {url}"
            )
            return None
        except requests.exceptions.RequestException as e:
            frappe.log_error(
                title="Provider API Error",
                message=f"Error calling {method.upper()} {url}: {e}"
            )
            return None

    def _get(self, endpoint, **kwargs):
        return self._request("GET", endpoint, **kwargs)

    def _post(self, endpoint, **kwargs):
        return self._request("POST", endpoint, **kwargs)

    def _put(self, endpoint, **kwargs):
        return self._request("PUT", endpoint, **kwargs)

    def _patch(self, endpoint, **kwargs):
        return self._request("PATCH", endpoint, **kwargs)

    def _delete(self, endpoint, **kwargs):
        return self._request("DELETE", endpoint, **kwargs)

    # ── Data sync methods (override in subclass) ──

    def fetch_plans(self):
        """Fetch available insurance plans/products from the provider.
        
        Returns a list of dicts with keys:
            plan_code, plan_name, plan_type, description,
            min_sum_assured, max_sum_assured, min_age, max_age,
            premium_frequency, min_term, max_term, status
        """
        raise NotImplementedError("Subclasses must implement fetch_plans()")

    def fetch_customer_policies(self, customer_ref):
        """Fetch policies for a given customer reference from the provider.
        
        Returns a list of dicts with keys:
            policy_number, plan_code, plan_name, status,
            sum_assured, premium_amount, premium_frequency,
            commencement_date, maturity_date, next_premium_date,
            nominee_name, nominee_relation
        """
        frappe.log_error(
            title="Provider API Not Implemented",
            message=f"fetch_customer_policies not implemented for {self.integration.name}"
        )
        return []

    def fetch_renewals(self, from_date=None, to_date=None):
        """Fetch upcoming renewals from the provider.
        
        Returns a list of dicts with keys:
            policy_number, renewal_date, premium_amount, status
        """
        return []

    def push_claim(self, claim_data):
        """Submit a claim to the provider.
        
        Args:
            claim_data: dict with policy_number, claim_type, claim_amount,
                       incident_date, description, documents, etc.
        
        Returns: (success: bool, message: str, reference: str|None)
        """
        return (False, "Not implemented", None)

    def push_policy_update(self, policy_data):
        """Send a policy update (endorsement, surrender, etc.) to the provider.
        
        Returns: (success: bool, message: str, reference: str|None)
        """
        return (False, "Not implemented", None)

    def verify_customer(self, customer_data):
        """Verify customer identity with the provider.
        
        Args:
            customer_data: dict with name, dob, pan/aadhaar, etc.
        
        Returns: (verified: bool, message: str, provider_ref: str|None)
        """
        return (False, "Not implemented", None)


# ──────────────────────────────────────────────
# Generic REST Client (fallback / config-based)
# ──────────────────────────────────────────────

class GenericProviderClient(BaseProviderClient):
    """A generic REST client for providers that follow standard REST patterns.

    Endpoints are derived from integration configuration:
      - GET  {base}/plans              -> fetch_plans()
      - GET  {base}/customers/{ref}/policies -> fetch_customer_policies()
      - GET  {base}/renewals           -> fetch_renewals()
      - POST {base}/claims             -> push_claim()
      - POST {base}/policies/{ref}     -> push_policy_update()
    """

    def fetch_plans(self):
        return self._get("plans") or []

    def fetch_customer_policies(self, customer_ref):
        return self._get(f"customers/{customer_ref}/policies") or []

    def fetch_renewals(self, from_date=None, to_date=None):
        params = {}
        if from_date:
            params["from"] = str(from_date)
        if to_date:
            params["to"] = str(to_date)
        return self._get("renewals", params=params) or []

    def push_claim(self, claim_data):
        result = self._post("claims", json=claim_data)
        if result and result.get("status") in ("ok", "submitted", "received"):
            return (True, "Claim submitted successfully", result.get("reference_no"))
        return (False, result.get("message", "Unknown error") if result else "No response", None)

    def push_policy_update(self, policy_data):
        policy_ref = policy_data.get("policy_number", "")
        result = self._put(f"policies/{policy_ref}", json=policy_data)
        if result and result.get("status") == "ok":
            return (True, "Policy updated", result.get("reference_no"))
        return (False, result.get("message", "Unknown error") if result else "No response", None)

    def verify_customer(self, customer_data):
        result = self._post("customers/verify", json=customer_data)
        if result:
            return (result.get("verified", False),
                    result.get("message", ""),
                    result.get("customer_ref"))
        return (False, "No response from provider", None)


# ──────────────────────────────────────────────
# LIC India Client
# ──────────────────────────────────────────────

class LICClient(BaseProviderClient):
    """Concrete client for LIC India's API.
    
    Typical LIC API endpoints (illustrative):
      - POST /api/v1/authenticate          -> get access token
      - GET  /api/v1/plans                  -> list plans
      - GET  /api/v1/policies/search?ref=   -> search policies by customer ref
      - GET  /api/v1/renewals?from=&to=     -> upcoming renewals
      - POST /api/v1/claims                 -> submit a claim
      - POST /api/v1/policies/verify        -> verify customer
    """

    API_VERSION = "v1"

    def _lic_request(self, method, endpoint, **kwargs):
        """LIC-specific request with auto-authentication."""
        return self._request(method, f"api/{self.API_VERSION}/{endpoint.lstrip('/')}", **kwargs)

    def _ensure_token(self):
        """For OAuth2 / token-based auth, refresh the token if expired."""
        if self.integration.auth_method != "OAuth2":
            return True  # Other auth methods don't need token refresh

        creds = self.integration.get_decrypted_credentials()
        if creds.get("access_token") and self.integration.token_expiry:
            expiry = self.integration.token_expiry
            if isinstance(expiry, str):
                from frappe.utils.data import get_datetime
                expiry = get_datetime(expiry)
            if now_datetime() < expiry:
                return True  # Token still valid

        # Token expired — refresh using client credentials
        auth_payload = {
            "client_id": creds.get("api_key") or "",
            "client_secret": creds.get("api_secret") or "",
            "grant_type": "client_credentials",
        }
        result = self._lic_request("POST", "authenticate", json=auth_payload)
        if result and result.get("access_token"):
            self.integration.db_set({
                "access_token": result["access_token"],
                "token_expiry": add_days(now_datetime(), result.get("expires_in_days", 30)),
            })
            return True

        frappe.log_error(
            title="LIC Auth Failed",
            message="Could not obtain access token from LIC API"
        )
        return False

    def fetch_plans(self):
        if not self._ensure_token():
            return []
        result = self._lic_request("GET", "plans")
        if not result:
            return []
        # LIC typically returns plans in a nested structure
        plans = result.get("data") or result.get("plans") or result.get("products") or []
        return self._normalize_plans(plans)

    def _normalize_plans(self, raw_plans):
        """Normalize LIC plan structure to the canonical format."""
        normalized = []
        for p in raw_plans:
            normalized.append({
                "plan_code": p.get("planCode") or p.get("plan_code") or p.get("code"),
                "plan_name": p.get("planName") or p.get("plan_name") or p.get("name"),
                "plan_type": p.get("planType") or p.get("plan_type") or p.get("category"),
                "description": p.get("description") or "",
                "min_sum_assured": p.get("minSumAssured") or p.get("min_sum_assured") or 0,
                "max_sum_assured": p.get("maxSumAssured") or p.get("max_sum_assured") or 0,
                "min_age": p.get("minAge") or p.get("min_age") or 18,
                "max_age": p.get("maxAge") or p.get("max_age") or 65,
                "premium_frequency": p.get("frequency") or p.get("premium_frequency") or "Yearly",
                "min_term": p.get("minTerm") or p.get("min_term") or 5,
                "max_term": p.get("maxTerm") or p.get("max_term") or 30,
                "status": p.get("status") or "Active",
            })
        return normalized

    def fetch_customer_policies(self, customer_ref):
        if not self._ensure_token():
            return []
        result = self._lic_request("GET", f"policies/search", params={"ref": customer_ref})
        if not result:
            return []
        policies = result.get("data") or result.get("policies") or []
        normalized = []
        for p in policies:
            normalized.append({
                "policy_number": p.get("policyNo") or p.get("policy_number") or p.get("policyNumber"),
                "plan_code": p.get("planCode") or p.get("plan_code"),
                "plan_name": p.get("planName") or p.get("plan_name"),
                "status": p.get("status") or p.get("policyStatus") or "Active",
                "sum_assured": p.get("sumAssured") or p.get("sum_assured") or 0,
                "premium_amount": p.get("premium") or p.get("premium_amount") or 0,
                "premium_frequency": p.get("frequency") or "Yearly",
                "commencement_date": p.get("commencementDate") or p.get("commencement_date"),
                "maturity_date": p.get("maturityDate") or p.get("maturity_date"),
                "next_premium_date": p.get("nextPremiumDate") or p.get("next_premium_date"),
                "nominee_name": p.get("nominee") or p.get("nominee_name"),
                "nominee_relation": p.get("nomineeRelation") or p.get("nominee_relation"),
            })
        return normalized

    def fetch_renewals(self, from_date=None, to_date=None):
        if not self._ensure_token():
            return []
        params = {}
        from_date = from_date or today()
        to_date = to_date or add_days(from_date, 30)
        params["from"] = str(from_date)
        params["to"] = str(to_date)
        result = self._lic_request("GET", "renewals", params=params)
        if not result:
            return []
        renewals = result.get("data") or result.get("renewals") or []
        normalized = []
        for r in renewals:
            normalized.append({
                "policy_number": r.get("policyNo") or r.get("policy_number"),
                "renewal_date": r.get("dueDate") or r.get("renewal_date") or r.get("due_date"),
                "premium_amount": r.get("premium") or r.get("premium_amount") or 0,
                "status": r.get("status") or "Due",
            })
        return normalized

    def push_claim(self, claim_data):
        if not self._ensure_token():
            return (False, "Authentication failed", None)
        payload = {
            "policyNo": claim_data.get("policy_number"),
            "claimType": claim_data.get("claim_type"),
            "claimAmount": claim_data.get("claim_amount"),
            "incidentDate": claim_data.get("incident_date"),
            "description": claim_data.get("description"),
            "documents": claim_data.get("documents", []),
        }
        result = self._lic_request("POST", "claims", json=payload)
        if result and result.get("status") in ("ok", "submitted"):
            return (True,
                    "Claim submitted to LIC",
                    result.get("claimReference") or result.get("reference_no"))
        return (False,
                result.get("message", "Unknown error") if result else "No response",
                None)

    def push_policy_update(self, policy_data):
        if not self._ensure_token():
            return (False, "Authentication failed", None)
        result = self._lic_request(
            "POST",
            f"policies/{policy_data.get('policy_number', '')}/update",
            json=policy_data,
        )
        if result and result.get("status") == "ok":
            return (True, "Policy updated on LIC", result.get("reference_no"))
        return (False,
                result.get("message", "Unknown error") if result else "No response",
                None)

    def verify_customer(self, customer_data):
        if not self._ensure_token():
            return (False, "Authentication failed", None)
        result = self._lic_request("POST", "policies/verify", json=customer_data)
        if result:
            return (result.get("verified", False),
                    result.get("message", ""),
                    result.get("customerRef") or result.get("customer_ref"))
        return (False, "No response from LIC", None)


# ──────────────────────────────────────────────
# HDFC Life Client (illustrative stub)
# ──────────────────────────────────────────────

class HDFCLifeClient(BaseProviderClient):
    """Concrete client for HDFC Life's API."""

    def fetch_plans(self):
        result = self._get("api/plans")
        return result.get("plans", []) if result else []


# ──────────────────────────────────────────────
# Sync Orchestration
# ──────────────────────────────────────────────

def sync_provider_integration(integration_name):
    """Run a full sync cycle for one provider integration.
    
    Called from the scheduled task or manually via API.
    """
    integration = _get_integration_doc(integration_name)
    if not integration.is_active or not integration.sync_enabled:
        return {"status": "skipped", "message": "Integration is not active"}

    integration.mark_sync_started()
    log = {"integration": integration_name, "steps": []}
    errors = []

    try:
        client = _get_client_for_integration(integration)

        # 1. Sync Plans / Products
        if integration.sync_plans:
            try:
                plans = client.fetch_plans()
                if plans:
                    count = _upsert_plans(integration.provider_name, plans)
                    step = {"step": "plans", "count": count, "status": "ok"}
                else:
                    step = {"step": "plans", "count": 0, "status": "no_data"}
                log["steps"].append(step)
            except Exception as e:
                msg = f"Plans sync failed: {e}"
                errors.append(msg)
                log["steps"].append({"step": "plans", "status": "failed", "error": str(e)})
                frappe.log_error(title="Provider Sync Error", message=msg)

        # 2. Sync Renewals
        if integration.sync_renewals:
            try:
                renewals = client.fetch_renewals()
                if renewals:
                    count = _upsert_renewals(integration.provider_name, renewals)
                    step = {"step": "renewals", "count": count, "status": "ok"}
                else:
                    step = {"step": "renewals", "count": 0, "status": "no_data"}
                log["steps"].append(step)
            except Exception as e:
                msg = f"Renewals sync failed: {e}"
                errors.append(msg)
                log["steps"].append({"step": "renewals", "status": "failed", "error": str(e)})
                frappe.log_error(title="Provider Sync Error", message=msg)

        # 3. Push Policy Updates (batch reconciliation for terminal statuses)
        if integration.push_policy_updates:
            try:
                pushed, failed = _push_policy_updates_for_provider(integration, client)
                step = {"step": "push_policy_updates", "pushed": pushed, "failed": failed, "status": "ok" if not failed else "partial"}
                log["steps"].append(step)
                if failed:
                    errors.append(f"{failed} policy update(s) failed")
            except Exception as e:
                msg = f"Policy updates push failed: {e}"
                errors.append(msg)
                log["steps"].append({"step": "push_policy_updates", "status": "failed", "error": str(e)})
                frappe.log_error(title="Provider Sync Error", message=msg)

        # 4. Verify Customers (batch reconciliation)
        if integration.sync_customers:
            try:
                verified, failed_cust = _verify_customers_for_provider(integration, client)
                step = {"step": "verify_customers", "verified": verified, "failed": failed_cust, "status": "ok" if not failed_cust else "partial"}
                log["steps"].append(step)
                if failed_cust:
                    errors.append(f"{failed_cust} customer(s) verification failed")
            except Exception as e:
                msg = f"Customer verification failed: {e}"
                errors.append(msg)
                log["steps"].append({"step": "verify_customers", "status": "failed", "error": str(e)})
                frappe.log_error(title="Provider Sync Error", message=msg)

        status = "Failed" if errors else "Success"
        message = "; ".join(errors) if errors else f"Synced {len(log['steps'])} data types"

    except Exception as e:
        status = "Failed"
        message = str(e)
        frappe.log_error(title="Provider Sync Error", message=f"Integration {integration_name} failed: {e}")

    integration.mark_sync_completed(status=status, message=message, log=log)
    return {"status": status, "message": message, "log": log}


def sync_all_providers():
    """Scheduled task: run sync for all active integrations whose interval has elapsed."""
    integrations = _get_active_integrations()
    results = []

    for integ in integrations:
        # Check if enough time has passed since last sync
        last_sync = integ.last_sync_end or integ.last_sync_start
        if last_sync:
            from frappe.utils.data import get_datetime
            last_dt = get_datetime(last_sync)
            elapsed_minutes = (now_datetime() - last_dt).total_seconds() / 60
            if elapsed_minutes < (integ.sync_interval_minutes or 1440):
                continue  # Not time yet

        result = sync_provider_integration(integ.name)
        results.append({"integration": integ.name, "result": result})

    if results:
        frappe.log_error(
            title="Provider Sync Summary",
            message=f"Synced {len(results)} integration(s): {frappe.as_json(results, indent=2)}"
        )

    return results


# ──────────────────────────────────────────────
# Data persistence helpers
# ──────────────────────────────────────────────

def _upsert_plans(provider_name, plans):
    """Sync fetched plans into Insurance Product doctype.
    
    Matches on product_code. Creates new products and updates existing ones.
    """
    count = 0
    for plan in plans:
        code = plan.get("plan_code")
        if not code:
            continue

        existing = frappe.db.get_value("Insurance Product", {"product_code": code}, "name")

        doc_data = {
            "product_name": plan.get("plan_name") or code,
            "product_code": code,
            "product_type": plan.get("plan_type") or "Life Insurance",
            "insurance_company": provider_name,
            "plan_type": plan.get("plan_type") or "Term",
            "min_age": plan.get("min_age") or 0,
            "max_age": plan.get("max_age") or 99,
            "min_sum_assured": plan.get("min_sum_assured") or 0,
            "max_sum_assured": plan.get("max_sum_assured") or 0,
            "premium_frequency": plan.get("premium_frequency") or "Yearly",
            "min_policy_term": plan.get("min_term") or 1,
            "max_policy_term": plan.get("max_term") or 30,
            "description": plan.get("description") or "",
            "status": plan.get("status") or "Active",
        }

        if existing:
            doc = frappe.get_doc("Insurance Product", existing)
            doc.update(doc_data)
            doc.flags.ignore_permissions = True
            doc.save()
        else:
            doc = frappe.get_doc(doctype="Insurance Product", **doc_data)
            doc.flags.ignore_permissions = True
            doc.insert()

        count += 1

    frappe.db.commit()
    return count


def _upsert_renewals(provider_name, renewals):
    """Sync fetched renewals into Policy Renewal doctype.
    
    Matches on policy number + renewal date. Only creates if not existing.
    """
    count = 0
    for rn in renewals:
        policy_no = rn.get("policy_number")
        renewal_date = rn.get("renewal_date")
        if not policy_no or not renewal_date:
            continue

        # Find the local policy by its number
        local_policy = frappe.db.get_value(
            "Insurance Policy",
            {"policy_number": policy_no},
            "name"
        )
        if not local_policy:
            continue

        # Check if renewal already exists
        exists = frappe.db.exists("Policy Renewal", {
            "policy": local_policy,
            "renewal_due_date": renewal_date,
        })
        if exists:
            continue

        renewal_doc = frappe.get_doc({
            "doctype": "Policy Renewal",
            "policy": local_policy,
            "renewal_due_date": renewal_date,
            "renewal_amount": rn.get("premium_amount", 0),
            "status": "Due",
        })
        renewal_doc.flags.ignore_permissions = True
        renewal_doc.insert()
        count += 1

    frappe.db.commit()
    return count



# ──────────────────────────────────────────────
# Batch sync helpers (called from sync_provider_integration)
# ──────────────────────────────────────────────

def _get_products_for_provider(provider_name):
    """Return list of Insurance Product names belonging to a provider."""
    return frappe.db.get_all(
        "Insurance Product",
        filters={"insurance_company": provider_name, "status": "Active"},
        pluck="name",
    )


def _push_policy_updates_for_provider(integration, client):
    """Batch push terminal status changes to the provider.
    
    Finds all policies linked to this provider's products that have
    terminal statuses (Surrendered, Lapsed, Matured, Claimed) and
    pushes updates via the API.
    """
    products = _get_products_for_provider(integration.provider_name)
    if not products:
        return 0, 0

    PUSHABLE_STATUSES = ("Surrendered", "Lapsed", "Matured", "Claimed")

    policies = frappe.db.get_all(
        "Insurance Policy",
        filters={
            "insurance_product": ["in", products],
            "policy_status": ["in", PUSHABLE_STATUSES],
        },
        fields=["name", "policy_number", "policy_status", "sum_assured"],
    )

    pushed = 0
    failed = 0
    statuses = {}

    for policy in policies:
        policy_data = {
            "policy_number": policy.policy_number or policy.name,
            "policy_status": policy.policy_status,
            "policy_amount": float(policy.sum_assured or 0),
        }
        success, message, reference = client.push_policy_update(policy_data)
        if success:
            pushed += 1
            s = policy.policy_status
            statuses[s] = statuses.get(s, 0) + 1
        else:
            failed += 1

    if pushed:
        frappe.log_error(
            title="Policy Updates Synced",
            message=(
                f"Pushed {pushed} policy update(s) to {integration.provider_name}: "
                + ", ".join(f"{n} {s}" for s, n in statuses.items())
                + (f" ({failed} failed)" if failed else "")
            )
        )

    return pushed, failed


def _verify_customers_for_provider(integration, client):
    """Batch verify customer identity with the provider.
    
    Finds Insurance Customers linked to policies from this provider
    and calls verify_customer on each.
    """
    products = _get_products_for_provider(integration.provider_name)
    if not products:
        return 0, 0

    # Get unique customers from policies linked to this provider's products
    customer_names = frappe.db.get_all(
        "Insurance Policy",
        filters={
            "insurance_product": ["in", products],
            "policy_status": "Active",
        },
        pluck="customer",
        distinct=True,
    )

    verified = 0
    failed = 0
    failed_names = []

    for cust_name in customer_names:
        # Use db.get_value instead of loading full doc
        cust = frappe.db.get_value(
            "Insurance Customer", cust_name,
            ["customer_name", "email_id", "mobile_no"],
            as_dict=True
        )
        if not cust:
            continue

        customer_data = {
            "name": cust.customer_name,
            "email": cust.email_id or "",
            "phone": cust.mobile_no or "",
        }

        success, message, provider_ref = client.verify_customer(customer_data)
        if success:
            verified += 1
        else:
            failed += 1
            failed_names.append(cust.customer_name)

    if verified or failed:
        frappe.log_error(
            title="Customer Verification Summary",
            message=(
                f"Verified {verified} customer(s) with {integration.provider_name}"
                + (f". Failed: {failed}: {', '.join(failed_names[:5])}" if failed else "")
            )
        )

    return verified, failed


# ──────────────────────────────────────────────
# Two-way push helpers (called from doc_events in hooks.py)
# ──────────────────────────────────────────────

def push_claim_to_provider(doc, method):
    """When an Insurance Claim is submitted, push it to the provider's API.
    Adds a note to claim_notes rather than changing claim_status (which has fixed options).
    """
    if doc.docstatus != 1:
        return

    # Find the integration for this claim's policy provider
    policy = frappe.get_doc("Insurance Policy", doc.insurance_policy) if doc.insurance_policy else None
    if not policy:
        return

    # Get the policy's product to find the provider
    product = frappe.get_doc("Insurance Product", policy.insurance_product) if policy.insurance_product else None
    if not product or not product.insurance_company:
        return

    provider_name = product.insurance_company
    integration_name = frappe.db.get_value(
        "Provider API Integration",
        {"provider_name": provider_name, "is_active": 1, "push_claims": 1},
        "name"
    )
    if not integration_name:
        return

    integration = _get_integration_doc(integration_name)
    client = _get_client_for_integration(integration)

    claim_data = {
        "policy_number": policy.policy_number or policy.name,
        "claim_type": doc.claim_type,
        "claim_amount": float(doc.claim_amount or 0),
        "incident_date": str(doc.incident_date or ""),
        "description": doc.incident_description or "",
    }

    success, message, reference = client.push_claim(claim_data)
    if success:
        ref_note = f" [Provider Ref: {reference}]" if reference else ""
        # Append to claim_notes instead of changing claim_status
        existing_notes = doc.claim_notes or ""
        note = f"\n<p><strong>Sent to {provider_name}</strong> — {now_datetime().strftime('%b %d, %Y %H:%M')}{ref_note}</p>"
        frappe.db.set_value("Insurance Claim", doc.name, "claim_notes", existing_notes + note)
        frappe.log_error(
            title="Claim Pushed to Provider",
            message=f"Claim {doc.name} pushed to {provider_name}. Ref: {reference}"
        )


def push_policy_update_to_provider(doc, method):
    """When a policy status changes to Surrendered or Lapsed, notify the provider.
    Only triggers on actual status change (not on every save).
    """
    if not doc.policy_status:
        return

    # Only push for terminal status changes that should be communicated to provider
    PUSHABLE_STATUSES = ("Surrendered", "Lapsed", "Matured", "Claimed")
    if doc.policy_status not in PUSHABLE_STATUSES:
        return

    # Check that status actually changed from previous value
    old_status = frappe.db.get_value("Insurance Policy", doc.name, "policy_status")
    if old_status == doc.policy_status:
        return  # Not a status change, skip

    product = frappe.get_doc("Insurance Product", doc.insurance_product) if doc.insurance_product else None
    if not product or not product.insurance_company:
        return

    provider_name = product.insurance_company
    integration_name = frappe.db.get_value(
        "Provider API Integration",
        {"provider_name": provider_name, "is_active": 1},
        "name"
    )
    if not integration_name:
        return

    integration = _get_integration_doc(integration_name)
    client = _get_client_for_integration(integration)

    policy_data = {
        "policy_number": doc.policy_number or doc.name,
        "policy_status": doc.policy_status,
        "policy_amount": float(doc.sum_assured or 0),
    }

    success, message, reference = client.push_policy_update(policy_data)
    if reference:
        frappe.log_error(
            title="Policy Update Pushed",
            message=f"Policy {doc.name} status changed from '{old_status}' to '{doc.policy_status}' — pushed to {provider_name}. Ref: {reference}"
        )
