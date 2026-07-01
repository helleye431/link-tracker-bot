def test_3_3(client):
    link = "https://github.com/helleye431/asteroids"
    header = {"tg-chat-id": "1"}
    undefined_header = {"tg-chat-id": "999"}
    response1 = client.post("/tg-chat/1")
    response2 = client.post(
        "/links",
        json={"link": link, "tags": ["test1", "test2"], "filters": ["test_filter"]},
        headers=header,
    )
    response3 = client.request(
        "DELETE", "/links", json={"link": link}, headers=undefined_header
    )
    response4 = client.get("/links", headers=header)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 404
    assert response4.json()["links"][0]["url"] == link
