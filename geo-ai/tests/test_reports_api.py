"""Tests for report delete endpoint."""


def test_delete_report(client, db_session_factory):
    from app.models.product import Product
    from app.models.report import Report

    db = db_session_factory()
    try:
        product = Product(name="ReportDeleteCo")
        db.add(product)
        db.commit()
        db.refresh(product)

        report = Report(
            product_id=product.id,
            file_path="/tmp/nonexistent_test_report.html",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id
        product_id = product.id
    finally:
        db.close()

    response = client.delete(f"/reports/{report_id}")
    assert response.status_code == 204

    list_response = client.get(f"/reports/{product_id}")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_missing_report_returns_404(client):
    response = client.delete("/reports/99999")
    assert response.status_code == 404
