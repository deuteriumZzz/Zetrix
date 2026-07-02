from rest_framework.exceptions import APIException
from rest_framework import status


class ScraperUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Scraper service is temporarily unavailable."


class AnalysisError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Could not analyze the provided data."


class ReportGenerationError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Report generation failed."
