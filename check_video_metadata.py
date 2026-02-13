from google.cloud import storage

def main():
    bucket_name = "islserver.appspot.com"
    blob_name = "upload/lenovo_p1/upload/lenovo_p1-5c963ab3-s001-2025-11-18T16:52:49.273236Z.mp4"  # use forward slashes

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Load metadata from GCS
    blob.reload()

    print("Bucket:     ", bucket_name)
    print("Object path:", blob_name)
    print("Created at: ", blob.time_created)
    print("Updated at: ", blob.updated)

if __name__ == "__main__":
    main()

