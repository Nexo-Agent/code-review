from app.services.repo_integrations import _infer_ado_org_project


def test_infer_ado_org_project_from_repo_full_name() -> None:
    org, project = _infer_ado_org_project(
        "azure-devops",
        "fabrikam/MyProject/MyRepo",
    )
    assert org == "fabrikam"
    assert project == "MyProject"


def test_infer_ado_org_project_empty_catch_all() -> None:
    assert _infer_ado_org_project("azure-devops", "") == ("", "")
    assert _infer_ado_org_project("azure-devops", "   ") == ("", "")


def test_infer_ado_org_project_github() -> None:
    assert _infer_ado_org_project("github", "acme/app") == ("", "")
