import logging

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class VirusScannerService:
    """
    Pluggable service to scan files for viruses.
    In production, this should integrate with ClamAV, AWS Macie, or an external API.
    """

    @classmethod
    def scan_file(cls, file_obj) -> None:
        """
        Scan a file object (in-memory or temporary disk) for viruses.
        Raises ValidationError if a virus is detected.
        """
        if not getattr(settings, "ENABLE_VIRUS_SCAN", False):
            return

        # Ensure we read from the beginning
        original_position = file_obj.tell() if hasattr(file_obj, "tell") else 0
        try:
            file_obj.seek(0)
            # ---------------------------------------------------------
            # TODO: Integrate real AV scanning here.
            # Example (ClamAV):
            # import pyclamd
            # cd = pyclamd.ClamdNetworkSocket()
            # result = cd.instream(file_obj)
            # if result and result.get('stream'):
            #     raise ValidationError(f"Virus detected: {result['stream'][1]}")
            # ---------------------------------------------------------
            
            # Simple EICAR test string detection for demonstration
            chunk = file_obj.read(1024)
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8", errors="ignore")
            if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" in chunk:
                logger.warning("EICAR test virus detected during upload.")
                raise ValidationError("Virus detected in file.")
        finally:
            file_obj.seek(original_position)
