import pandas as pd


def get_english_description(descriptions):
    """Return the first English description, or '' if none."""
    if isinstance(descriptions, list):
        for desc in descriptions:
            if desc.get("lang") == "en":
                return desc.get("value")
    return ""


def _pick_primary_or_first(metrics):
    """From a list of CVSS metrics pick the 'Primary' entry, or the first available one."""
    if not isinstance(metrics, list) or not metrics:
        return None
    for entry in metrics:
        if isinstance(entry, dict) and entry.get("type") == "Primary":
            return entry
    return metrics[0] if isinstance(metrics[0], dict) else None

def extract_cvss_data(row):
    """
    Extracts CVSS fields from V3.1 or V3.0.
    Always returns a dict (possibly empty), with keys prefixed with 'cvss_'.
    """
    for version_key in ("cve.metrics.cvssMetricV31", "cve.metrics.cvssMetricV30"):
        metrics = row.get(version_key)
        entry = _pick_primary_or_first(metrics)
        if entry:
            data = entry.get("cvssData") or {}
            if isinstance(data, dict):
                return {f"cvss_{k}": v for k, v in data.items()}
    return {}


def extract_vulnerable_cpes(configs):
    """Collect all CPEs marked as 'vulnerable'"""
    cpes = []
    if isinstance(configs, list):
        for conf in configs:
            for node in conf.get("nodes", []):
                for cpe in node.get("cpeMatch", []):
                    if cpe.get("vulnerable", False):
                        cpes.append(cpe.get("criteria"))
    return cpes


def extract_cwes(weaknesses):
    """Extract the list of CWE identifiers in format 'CWE-XXXX' from descriptions."""
    cwe_list = []
    if isinstance(weaknesses, list):
        for item in weaknesses:
            for desc in item.get("description", []):
                value = desc.get("value")
                if value and value.startswith("CWE-"):
                    cwe_list.append(value)
    return cwe_list


def preprocess_NVD_data(df):
    """
    - Convert date fields
    - Extract English description, CVSS data, vulnerable CPEs, CWEs, number of references
    - Drop raw columns that are no longer needed
    """
    df = df.copy()
    
    # Convert date fields
    df["cve.published"] = pd.to_datetime(df["cve.published"])
    df["cve.lastModified"] = pd.to_datetime(df["cve.lastModified"])

    # Extract English description, CVSS data, vulnerable CPEs, CWEs, number of references
    df['description'] = df['cve.descriptions'].apply(get_english_description)
    df["vulnerable_cpes"] = df["cve.configurations"].apply(extract_vulnerable_cpes)
    df["num_references"] = df["cve.references"].apply(lambda refs: len(refs) if isinstance(refs, list) else 0)
    df["cwe_list"] = df["cve.weaknesses"].apply(extract_cwes)
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    cvss_expanded = df.apply(lambda row: pd.Series(extract_cvss_data(row)), axis=1)
    df = pd.concat([df, cvss_expanded], axis=1)
    df["cvss_baseSeverity"] = pd.Categorical(df["cvss_baseSeverity"], categories=severity_order, ordered=True)
    
    # Drop raw columns that are no longer needed
    df = df.drop(['cve.descriptions',
                  'cve.cveTags',
                  'cve.metrics.cvssMetricV40', 
                  'cve.metrics.cvssMetricV31',
                  'cve.metrics.cvssMetricV30',
                  'cve.metrics.cvssMetricV2', 
                  'cve.configurations', 
                  'cve.weaknesses'],
                 axis=1)
    return df
    
