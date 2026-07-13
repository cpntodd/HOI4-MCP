<!-- GAP-010:COMPLETED -->

FROM python:3.12-slim

LABEL org.opencontainers.image.title="HOI4-MCP Server"
LABEL org.opencontainers.image.description="MCP server for Hearts of Iron IV modding — indexer, validator, vanilla DB lookup, error log parsing, and adaptive learning"
LABEL org.opencontainers.image.source="https://github.com/cpntodd/HOI4-MCP"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python package
COPY hoi4-mcp-server/ /app/
RUN pip install --no-cache-dir -e .

# Default command — override mod-path and vanilla-db via environment
ENV HOI4_MOD_PATH=""
ENV HOI4_VANILLA_DB="/data/vanilla.db"
ENV HOI4_ERROR_LOG=""

VOLUME ["/data", "/mod"]

ENTRYPOINT ["python", "-m", "hoi4_mcp.server"]
CMD ["--vanilla-db", "/data/vanilla.db", "--auto-detect-mod"]
