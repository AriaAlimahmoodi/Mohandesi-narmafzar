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
@pytest.mark.django_db
def test_public_file_download_requires_published_resource():
    librarian = User.objects.create_user(
        username="download_librarian",
        password="strong-pass-123",
        role=User.Role.LIBRARIAN,
    )

    librarian_client = APIClient()
    librarian_client.force_authenticate(librarian)

    pdf_file = io.BytesIO(b"%PDF-1.7\nminimal test pdf")
    pdf_file.name = "download-test.pdf"

    response = librarian_client.post(
        "/api/v1/resources/",
        {
            "title": "Download Test Book",
            "file": pdf_file,
        },
        format="multipart",
    )

    assert response.status_code == 201

    resource = Resource.objects.get(pk=response.data["id"])
    resource_file = resource.files.get(is_active=True)

    download_url = (
        f"/api/v1/resources/{resource.id}/files/"
        f"{resource_file.id}/download/"
    )

    guest_client = APIClient()

    # Draft resources must not be downloadable by guests.
    response = guest_client.get(download_url)
    assert response.status_code == 404

    # Published public resources must be downloadable by guests.
    resource.status = Resource.Status.PUBLISHED
    resource.access_policy = Resource.AccessPolicy.PUBLIC
    resource.save()

    response = guest_client.get(download_url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"".join(response.streaming_content) == b"%PDF-1.7\nminimal test pdf"