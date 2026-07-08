"""Tests for product CRUD including delete."""


def test_delete_product(client):
    create = client.post("/products", json={"name": "ToDelete"})
    assert create.status_code == 201
    product_id = create.json()["id"]

    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 204

    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404


def test_delete_missing_product_returns_404(client):
    response = client.delete("/products/99999")
    assert response.status_code == 404
