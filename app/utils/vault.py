import os
import logging
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient, KeyVaultSecret

class Vault:
    """
    A class for managing interactions with Azure Key Vault.

    This class provides methods for initializing a connection to Azure Key Vault
    and retrieving secrets from it.

    Attributes:
        vault_url (str): The URL of the Azure Key Vault.
        credential (DefaultAzureCredential): The credential used for authentication.
        client (SecretClient): The client used to interact with Azure Key Vault.
    """

    def __init__(self) -> None:
        try:
            vault_url: str = os.environ['AZ_KEYVAULT_URL']
            credential: DefaultAzureCredential = DefaultAzureCredential()
            self.client: SecretClient = SecretClient(vault_url=vault_url, credential=credential)
        except Exception as e:
            logging.critical(f'Azure Key Vault initialization error: {e}')
            raise

    def get_secret(self, secret_name: str) -> Optional[str]:
        try:
            secret: KeyVaultSecret = self.client.get_secret(secret_name)
            logging.info(f"Retrieving secret: {secret.name}")
            return secret.value
        except Exception as e:
            logging.error(f"Failed to access Azure Key Vault: {e}")
            return None