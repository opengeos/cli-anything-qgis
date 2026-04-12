"""Processing framework operations — list and run QGIS algorithms."""

import json

from cli_anything.qgis.utils.qgis_backend import ensure_qgis

_processing_initialized = False


def _init_processing():
    """Initialize the QGIS processing framework."""
    global _processing_initialized
    if _processing_initialized:
        return

    ensure_qgis()
    from qgis.core import QgsApplication

    # Initialize native algorithms
    from qgis.analysis import QgsNativeAlgorithms

    if not QgsApplication.processingRegistry().providerById("native"):
        QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    _processing_initialized = True


def list_algorithms(provider=None, search=None):
    """List available processing algorithms.

    Args:
        provider: Filter by provider ID (e.g., 'native', 'gdal', 'qgis').
        search: Search string to filter algorithm names/descriptions.

    Returns:
        dict with algorithm list.
    """
    _init_processing()
    from qgis.core import QgsApplication

    registry = QgsApplication.processingRegistry()
    algorithms = []

    for alg in registry.algorithms():
        if provider and alg.provider().id() != provider:
            continue
        if search:
            search_lower = search.lower()
            if (
                search_lower not in alg.id().lower()
                and search_lower not in alg.displayName().lower()
            ):
                continue

        algorithms.append(
            {
                "id": alg.id(),
                "name": alg.displayName(),
                "group": alg.group(),
                "provider": alg.provider().id(),
            }
        )

    return {
        "action": "list_algorithms",
        "count": len(algorithms),
        "provider_filter": provider,
        "search_filter": search,
        "algorithms": algorithms,
    }


def algorithm_info(algorithm_id):
    """Get detailed info about a processing algorithm.

    Args:
        algorithm_id: The algorithm ID (e.g., 'native:buffer').

    Returns:
        dict with algorithm details including parameters.
    """
    _init_processing()
    from qgis.core import QgsApplication

    registry = QgsApplication.processingRegistry()
    alg = registry.algorithmById(algorithm_id)
    if not alg:
        raise ValueError(f"Algorithm not found: {algorithm_id}")

    params = []
    for param in alg.parameterDefinitions():
        p = {
            "name": param.name(),
            "description": param.description(),
            "type": param.type(),
            "optional": (
                not (param.flags() & param.Flag.FlagOptional) == 0
                if hasattr(param, "Flag")
                else False
            ),
        }
        if hasattr(param, "defaultValue") and param.defaultValue() is not None:
            p["default"] = str(param.defaultValue())
        params.append(p)

    outputs = []
    for output in alg.outputDefinitions():
        outputs.append(
            {
                "name": output.name(),
                "description": output.description(),
                "type": output.type(),
            }
        )

    return {
        "action": "algorithm_info",
        "id": alg.id(),
        "name": alg.displayName(),
        "group": alg.group(),
        "provider": alg.provider().id(),
        "short_help": alg.shortHelpString() or "",
        "parameters": params,
        "outputs": outputs,
    }


def run_algorithm(algorithm_id, parameters, feedback_callback=None):
    """Run a processing algorithm.

    Args:
        algorithm_id: The algorithm ID (e.g., 'native:buffer').
        parameters: Dict of parameter name -> value mappings.
        feedback_callback: Optional callable(progress_pct) for progress updates.

    Returns:
        dict with algorithm results.
    """
    _init_processing()
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    class CaptureFeedback(QgsProcessingFeedback):
        def __init__(self, callback=None):
            super().__init__()
            self._callback = callback
            self.log_messages = []

        def setProgressText(self, text):
            self.log_messages.append(text)

        def pushInfo(self, info):
            self.log_messages.append(info)

        def pushWarning(self, warning):
            self.log_messages.append(f"WARNING: {warning}")

        def reportError(self, error, fatalError=False):
            self.log_messages.append(f"ERROR: {error}")

        def setProgress(self, progress):
            if self._callback:
                self._callback(progress)

    context = QgsProcessingContext()
    feedback = CaptureFeedback(feedback_callback)

    import processing as qgis_processing

    results = qgis_processing.run(
        algorithm_id,
        parameters,
        context=context,
        feedback=feedback,
    )

    # Serialize results
    serialized = {}
    for key, value in results.items():
        if hasattr(value, "source"):
            serialized[key] = value.source()
        elif hasattr(value, "id"):
            serialized[key] = str(value.id())
        else:
            serialized[key] = str(value) if value is not None else None

    return {
        "action": "run_algorithm",
        "algorithm": algorithm_id,
        "parameters": {k: str(v) for k, v in parameters.items()},
        "results": serialized,
        "log": feedback.log_messages[-20:] if feedback.log_messages else [],
    }


def list_providers():
    """List available processing providers.

    Returns:
        dict with provider list.
    """
    _init_processing()
    from qgis.core import QgsApplication

    registry = QgsApplication.processingRegistry()
    providers = []

    for provider in registry.providers():
        alg_count = len(provider.algorithms())
        providers.append(
            {
                "id": provider.id(),
                "name": provider.name(),
                "algorithm_count": alg_count,
            }
        )

    return {
        "action": "list_providers",
        "count": len(providers),
        "providers": providers,
    }
