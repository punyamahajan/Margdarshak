"""Tests for authentication and student profile management."""

import uuid
import pytest
import httpx

from app.main import app


@pytest.mark.anyio
async def test_auth_signup_login_and_profile_flow():
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"student_{unique_suffix}@demo.edu"
    student_id = f"ID-{unique_suffix}"
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sign up
        signup_payload = {
            "name": "Rohan Sharma",
            "email": email,
            "password": "Password@123",
            "college_name": "Indian Institute of Technology",
            "student_id": student_id,
            "branch": "Computer Science",
            "phone": "+91 9876543210",
            "known_subjects": ["Data Structures", "Algorithms", "Python"],
            "explore_topics": ["Distributed Systems", "Cloud Computing"],
        }
        resp = await client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "access_token" in data
        student = data["student"]
        assert student["name"] == "Rohan Sharma"
        assert student["college_name"] == "Indian Institute of Technology"
        assert student["student_id"] == student_id
        assert student["known_subjects"] == ["Data Structures", "Algorithms", "Python"]
        assert student["explore_topics"] == ["Distributed Systems", "Cloud Computing"]
        
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get profile via /me
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email
        
        # 3. Update profile (add new subjects and topics)
        update_payload = {
            "known_subjects": ["Data Structures", "Algorithms", "Python", "SQL", "DBMS"],
            "explore_topics": ["Distributed Systems", "Machine Learning", "Kubernetes"],
            "college_name": "IIT Delhi",
        }
        update_resp = await client.put("/api/v1/auth/profile", json=update_payload, headers=headers)
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["college_name"] == "IIT Delhi"
        assert "SQL" in updated["known_subjects"]
        assert "Machine Learning" in updated["explore_topics"]
        
        # 4. Log in via email
        login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
        assert login_resp.status_code == 200
        assert login_resp.json()["student"]["college_name"] == "IIT Delhi"

        # 5. Log in via student_id
        login_id_resp = await client.post("/api/v1/auth/login", json={"email": student_id, "password": "Password@123"})
        assert login_id_resp.status_code == 200
        assert login_id_resp.json()["student"]["email"] == email
