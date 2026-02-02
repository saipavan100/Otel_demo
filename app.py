from flask import Flask, jsonify
import logging
import time
import random
import os

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider

# Resource info
resource = Resource.create({
    "service.name": "otel-sample-app",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})

# Get OTel Collector endpoint from environment variable
OTEL_COLLECTOR_ENDPOINT = os.getenv("OTEL_COLLECTOR_ENDPOINT", "otel-collector:4317")

# Tracing setup
trace_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)
otlp_trace_exporter = OTLPSpanExporter(endpoint=f"http://{OTEL_COLLECTOR_ENDPOINT}", insecure=True)
trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))

# Metrics setup (OTLP)
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=f"http://{OTEL_COLLECTOR_ENDPOINT}", insecure=True)
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Logging setup (OTLP)
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
otlp_log_exporter = OTLPLogExporter(endpoint=f"http://{OTEL_COLLECTOR_ENDPOINT}", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))

# Configure Python logging to use OTLP
logging.basicConfig(level=logging.INFO)
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logger = logging.getLogger("otel-sample-app")

# Flask app
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Prometheus metrics for /metrics endpoint
prom_request_counter = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
prom_request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# OTel metrics
otel_request_counter = meter.create_counter(
    "app.requests.total",
    description="Total requests received"
)
otel_request_duration = meter.create_histogram(
    "app.request.duration",
    description="Request duration in seconds"
)

# Middleware to track metrics and add endpoint context to logs
@app.before_request
def before_request():
    from flask import request, g
    import logging
    g.start_time = time.time()
    
    # Add endpoint info to log context
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.http_method = request.method
        record.http_endpoint = request.path
        record.http_url = request.url
        return record
    
    logging.setLogRecordFactory(record_factory)

@app.after_request
def after_request(response):
    from flask import request, g
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        prom_request_counter.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        prom_request_duration.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)
        
        otel_request_counter.add(1, {"endpoint": request.path, "method": request.method})
        otel_request_duration.record(duration, {"endpoint": request.path})
    
    return response

@app.route("/")
def hello():
    from flask import request
    logger.info(f"Processing request to {request.path}")
    with tracer.start_as_current_span("hello-span") as span:
        span.set_attribute("custom.attribute", "hello-world")
        span.set_attribute("http.endpoint", request.path)
        time.sleep(random.uniform(0.1, 0.3))
        logger.info(f"Successfully processed {request.path}")
        return jsonify({"message": "Hello from OTel Sample App!", "status": "success"})

@appfrom flask import request
    logger.info(f"Fetching users list from {request.path}")
    with tracer.start_as_current_span("get-users") as span:
        span.set_attribute("users.count", 3)
        span.set_attribute("http.endpoint", request.path)
        # Simulate database query
        time.sleep(random.uniform(0.05, 0.15))
        users = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        logger.info(f"Retrieved {len(users)} users from {request.path}
        ]
        logger.info(f"Retrieved {len(users)} users")
        return jsonify({"users": users})

@appfrom flask import request
    logger.info(f"Fetching user with id: {user_id} from {request.path}")
    with tracer.start_as_current_span("get-user-by-id") as span:
        span.set_attribute("user.id", user_id)
        span.set_attribute("http.endpoint", request.path)
        
        # Simulate database lookup
        time.sleep(random.uniform(0.05, 0.2))
        
        if user_id > 10:
            logger.warning(f"User {user_id} not found at {request.path}")
            span.set_attribute("error", True)
            return jsonify({"error": "User not found"}), 404
        
        user = {"id": user_id, "name": f"User{user_id}", "email": f"user{user_id}@example.com"}
        logger.info(f"Retrieved user: {user['name']} from {request.path
        user = {"id": user_id, "name": f"User{user_id}", "email": f"user{user_id}@example.com"}
        logger.info(f"Retrieved user: {user['name']}")
        return jsonify({"user": user})

@appfrom flask import request
    logger.info(f"Creating new order at {request.path}")
    with tracer.start_as_current_span("create-order") as span:
        span.set_attribute("http.endpoint", request.path)
        # Simulate order creation with nested spans
        with tracer.start_as_current_span("validate-order"):
            time.sleep(random.uniform(0.02, 0.05))
            logger.debug("Order validated")
        
        with tracer.start_as_current_span("process-payment"):
            time.sleep(random.uniform(0.1, 0.2))
            logger.debug("Payment processed")
        
        with tracer.start_as_current_span("update-inventory"):
            time.sleep(random.uniform(0.03, 0.08))
            logger.debug("Inventory updated")
        
        order_id = random.randint(1000, 9999)
        span.set_attribute("order.id", order_id)
        logger.info(f"Order {order_id} created successfully at {request.path
        span.set_attribute("order.id", order_id)
        logger.info(f"Order created successfully with id: {order_id}")
        return jsonify({"order_id": order_id, "status": "created"})

@appfrom flask import request
    logger.error(f"Simulating an error scenario at {request.path}")
    with tracer.start_as_current_span("error-endpoint") as span:
        span.set_attribute("error", True)
        span.set_attribute("error.type", "SimulatedError")
        span.set_attribute("http.endpoint", request.path)
        try:
            raise ValueError("This is a simulated error for testing")
        except Exception as e:
            logger.exception(f"An error occurred at {request.path}ed error for testing")
        except Exception as e:
            logger.exception("An error occurred")
            span.record_exception(e)
    from flask import request
    logger.info(f"Processing slow request at {request.path}")
    with tracer.start_as_current_span("slow-endpoint") as span:
        span.set_attribute("http.endpoint", request.path)
        delay = random.uniform(1, 3)
        span.set_attribute("delay.seconds", delay)
        logger.info(f"Simulating slow operation for {delay:.2f} seconds at {request.path}")
        time.sleep(delay)
        logger.info(f"Slow operation completed at {request.path}
        span.set_attribute("delay.seconds", delay)
        logger.info(f"Simulating slow operation for {delay:.2f} seconds")
        time.sleep(delay)
        logger.info("Slow operation completed")
        return jsonify({"message": "Slow operation completed", "delay": delay})

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "otel-sample-app"})

if __name__ == "__main__":
    logger.info("Starting OTel Sample Application")
    app.run(host="0.0.0.0", port=5000)
