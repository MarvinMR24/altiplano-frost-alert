from tests.conftest import login, square

CH = {"push": True, "email": False}


def test_create_inside_coverage(client, app):
    h = login(client, app)
    r = client.post("/aois", headers=h, json={"name": "Chacra", "polygon": square(-68.2, -16.5), "threshold": 50,
                                              "channels": CH})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["current"]["cell_used"] == "el_alto" and body["current"]["distance_km"] < 1
    assert body["current"]["level"] in {"low", "moderate", "high", "very_high"}
    assert [a["id"] for a in client.get("/aois", headers=h).json()] == [body["id"]]


def test_outside_coverage_is_422(client, app):
    h = login(client, app)
    r = client.post("/aois", headers=h, json={"name": "La Paz far", "polygon": square(-66.0, -15.0), "threshold": 50,
                                              "channels": CH})
    assert r.status_code == 422 and "coverage" in r.json()["detail"]
    # Partly outside: a large box centered on El Alto that crosses the circle edge.
    r = client.post("/aois", headers=h, json={"name": "edge", "polygon": square(-68.2, -16.5, half=0.3),
                                              "threshold": 50, "channels": CH})
    assert r.status_code == 422


def test_bad_polygons_are_422(client, app):
    h = login(client, app)
    bowtie = {"type": "Polygon", "coordinates": [[[-68.21, -16.51], [-68.19, -16.49], [-68.19, -16.51],
                                                  [-68.21, -16.49], [-68.21, -16.51]]]}
    unclosed = {"type": "Polygon", "coordinates": [[[-68.21, -16.51], [-68.19, -16.51], [-68.19, -16.49]]]}
    many = {"type": "Polygon", "coordinates": [[[-68.2 + 0.01 * i, -16.5 + 0.001 * (i % 2)] for i in range(13)]
                                               + [[-68.2, -16.6], [-68.2, -16.5]]]}
    tiny = square(-68.2, -16.5, half=0.0001)
    two_points = {"type": "Polygon", "coordinates": [[[-68.21, -16.51], [-68.19, -16.51], [-68.21, -16.51]]]}
    for poly in (bowtie, unclosed, many, tiny, two_points):
        r = client.post("/aois", headers=h, json={"name": "bad", "polygon": poly, "threshold": 50, "channels": CH})
        assert r.status_code == 422, (poly, r.text)
    r = client.post("/aois", headers=h, json={"name": "bad", "polygon": square(-68.2, -16.5), "threshold": 40,
                                              "channels": CH})
    assert r.status_code == 422


def test_patch_and_delete_and_ownership(client, app):
    h = login(client, app, "owner@example.com")
    aoi = client.post("/aois", headers=h, json={"name": "a", "polygon": square(-67.1, -18.0), "threshold": 30,
                                                "channels": CH}).json()
    r = client.patch(f"/aois/{aoi['id']}", headers=h, json={"threshold": 70, "channels": {"push": False, "email": True}})
    assert r.status_code == 200 and r.json()["threshold"] == 70 and r.json()["channels"]["email"] is True
    intruder = login(client, app, "intruder@example.com")
    assert client.patch(f"/aois/{aoi['id']}", headers=intruder, json={"name": "x"}).status_code == 404
    assert client.delete(f"/aois/{aoi['id']}", headers=intruder).status_code == 404
    assert client.delete(f"/aois/{aoi['id']}", headers=h).status_code == 204
    assert client.get("/aois", headers=h).json() == []


def test_coverage_geojson(client, app):
    h = login(client, app)
    cov = client.get("/coverage", headers=h).json()
    assert cov["type"] == "FeatureCollection" and cov["meta"]["radius_km"] == 30
    assert {f["properties"]["point_id"] for f in cov["features"]} == {
        "el_alto", "oruro", "patacamaya", "calamarca", "caracollo", "corocoro", "charana", "huanuni"}
    ring = cov["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
