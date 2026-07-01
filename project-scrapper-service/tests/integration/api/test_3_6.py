def test_3_6(client):
    response1 = client.delete("/tg-chat/1")
    assert response1.status_code == 404
