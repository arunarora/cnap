from abc import ABC, abstractmethod

class BaseGatewayHandler(ABC):
    """
    Abstract Base Class that all Gateway Handlers must inherit from.
    This ensures consistency across different gateway implementations.
    """

    @abstractmethod
    def process_application(self, spec, name, namespace, logger, **kwargs):
        """
        Process the Application CRD spec.
        
        Args:
            spec (dict): The 'spec' field of the CRD.
            name (str): Name of the Application resource.
            namespace (str): Namespace of the resource.
            logger: Kopf logger object.
        """
        pass