from rest_framework import serializers
from .models import Author, Category, Resource, ResourceFile
from .services import register_resource
class AuthorSerializer(serializers.ModelSerializer):
    class Meta: model=Author; fields=("id","name")
class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=Category; fields=("id","name","parent")
class ResourceFileSerializer(serializers.ModelSerializer):
    class Meta: model=ResourceFile; fields=("id","file_type","size_bytes","sha256","version","is_active","created_at","file"); read_only_fields=("id","file_type","size_bytes","sha256","version","is_active","created_at")
class ResourceSerializer(serializers.ModelSerializer):
    authors=AuthorSerializer(many=True,read_only=True)
    author_ids=serializers.PrimaryKeyRelatedField(many=True,source="authors",queryset=Author.objects.all(),write_only=True,required=False)
    category=CategorySerializer(read_only=True)
    category_id=serializers.PrimaryKeyRelatedField(source="category",queryset=Category.objects.all(),write_only=True,required=False,allow_null=True)
    files=ResourceFileSerializer(many=True,read_only=True)
    file=serializers.FileField(write_only=True,required=False)
    class Meta:
        model=Resource
        fields=("id","title","authors","author_ids","publisher","publication_year","language","category","category_id","keywords","description","isbn","cover_url","status","access_policy","files","file","created_at","updated_at")
        read_only_fields=("id","created_at","updated_at","files")
    def create(self,validated_data):
        uploaded=validated_data.pop("file",None); authors=validated_data.pop("authors",[])
        if not uploaded: raise serializers.ValidationError({"file":"A resource file is required."})
        resource=register_resource(user=self.context["request"].user,resource_data=validated_data,uploaded_file=uploaded); resource.authors.set(authors); return resource
    def update(self,instance,validated_data):
        validated_data.pop("file",None); authors=validated_data.pop("authors",None)
        for k,v in validated_data.items(): setattr(instance,k,v)
        instance.save()
        if authors is not None: instance.authors.set(authors)
        return instance
