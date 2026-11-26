import io, pytest
from rest_framework.test import APIClient
from apps.identity.models import User
from apps.resources.models import Resource
@pytest.mark.django_db
def test_register_and_login():
    c=APIClient(); r=c.post("/api/v1/auth/register/",{"username":"aria","password":"strong-pass-123"},format="json"); assert r.status_code==201
    r=c.post("/api/v1/auth/login/",{"username":"aria","password":"strong-pass-123"},format="json"); assert r.status_code==200 and "access" in r.data
@pytest.mark.django_db
def test_guest_only_gets_public_published():
    u=User.objects.create_user(username="lib",password="strong-pass-123",role=User.Role.LIBRARIAN)
    Resource.objects.create(title="Public",status="PUBLISHED",access_policy="PUBLIC",created_by=u)
    Resource.objects.create(title="Draft",status="DRAFT",access_policy="PUBLIC",created_by=u)
    Resource.objects.create(title="Private",status="PUBLISHED",access_policy="REGISTERED_ONLY",created_by=u)
    r=APIClient().get("/api/v1/resources/"); assert r.status_code==200 and [x["title"] for x in r.data]==["Public"]
@pytest.mark.django_db
def test_librarian_can_register_pdf():
    u=User.objects.create_user(username="lib2",password="strong-pass-123",role=User.Role.LIBRARIAN); c=APIClient(); c.force_authenticate(u)
    f=io.BytesIO(b"%PDF-1.7\nminimal"); f.name="book.pdf"
    r=c.post("/api/v1/resources/",{"title":"Book","file":f},format="multipart"); assert r.status_code==201
