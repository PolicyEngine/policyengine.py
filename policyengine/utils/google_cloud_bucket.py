def download_file_from_gcs(
    bucket_name: str, file_name: str, destination_path: str
) -> None:
    """
    Download a file from Google Cloud Storage to a local path.

    Args:
        bucket_name (str): The name of the GCS bucket.
        file_name (str): The name of the file in the GCS bucket.
        destination_path (str): The local path where the file will be saved.

    Returns:
        None
    """
    from google.cloud import storage

    # Initialize a client
    client = storage.Client()

    # Get the bucket
    bucket = client.bucket(bucket_name)

    # Create a blob object from the file name
    blob = bucket.blob(file_name)

    # Download the file to a local path
    blob.download_to_filename(destination_path)

    return destination_path
