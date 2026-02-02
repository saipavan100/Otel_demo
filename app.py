from flask import Flask
import logging, time, random

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Resource info
resource = Resource.create({"service.name": "otel-sample-app"})

# Tracing setup
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Metrics setup
metrics.set_meter_provider(MeterProvider(resource=resource))
meter = metrics.get_meter(__name__)
reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
metrics.get_meter_provider().add_metric_reader(reader)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("otel-sample")

# Flask app
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Example metric
request_counter = meter.create_counter("requests_total", description="Total requests received")

@app.route("/")
def hello():
    request_counter.add(1)
    logger.info("Processing request at /")
    with tracer.start_as_current_span("hello-span"):
        time.sleep(random.uniform(0.1, 0.3))
        return "Hello from OTel Sample App with Jaeger!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
