import os
from pinecone import Pinecone, ServerlessSpec

# TODO: Add error handling and logging


class PineconeClient:
    def __init__(self):
        self.api_key = os.environ.get("PINECONE_API_KEY")
        self.environment = os.environ.get("PINECONE_ENVIRONMENT")
        if not self.api_key or not self.environment:
            raise ValueError(
                "PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set in environment variables"
            )

        self.pinecone = Pinecone(api_key=self.api_key, environment=self.environment)

    def get_index(self, index_name: str):
        return self.pinecone.Index(index_name)

    def create_index(self, index_name: str, dimension: int, metric: str = "cosine"):
        if index_name not in self.pinecone.list_indexes().names:
            self.pinecone.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud="aws",  # Specify your cloud provider
                    region="us-west-2",  # Specify your region
                ),
            )
            return f"Index {index_name} created successfully."
        return f"Index {index_name} already exists."

    def delete_index(self, index_name: str):
        if index_name in self.pinecone.list_indexes().names:
            self.pinecone.delete_index(index_name)
            return f"Index {index_name} deleted successfully."
        return f"Index {index_name} does not exist."


# Example usage (optional - for testing purposes)
if __name__ == "__main__":
    # Ensure PINECONE_API_KEY and PINECONE_ENVIRONMENT are set in your environment
    # For example, in your .env file or shell export
    # export PINECONE_API_KEY='YOUR_API_KEY'
    # export PINECONE_ENVIRONMENT='YOUR_ENVIRONMENT'

    client = PineconeClient()
    index_name = "my-test-index"
    dimension = 1536  # Example dimension, adjust as needed for your embeddings

    # print(client.create_index(index_name, dimension))
    # index = client.get_index(index_name)
    # print(index.describe_index_stats())
    # print(client.delete_index(index_name))
    print(
        "Pinecone client initialized. Ensure API key and environment are correctly set."
    )
