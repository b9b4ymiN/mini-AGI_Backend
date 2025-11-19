#!/bin/bash

# =============================================================================
# Mini-AGI Backend - Deployment Script
# =============================================================================
# This script automates the deployment process
#
# Usage:
#   ./deploy.sh dev          # Development deployment
#   ./deploy.sh prod         # Production deployment
#   ./deploy.sh stop         # Stop all services
#   ./deploy.sh logs         # View logs
#   ./deploy.sh pull-model   # Pull Ollama model
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

check_dependencies() {
    print_info "Checking dependencies..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "Dependencies checked"
}

setup_env() {
    if [ ! -f .env ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created"
        print_info "Please edit .env file with your configuration"
        print_info "Press Enter to continue..."
        read
    else
        print_success ".env file exists"
    fi
}

deploy_dev() {
    print_info "Starting development deployment..."

    check_dependencies
    setup_env

    print_info "Building and starting services..."
    docker-compose up -d --build

    print_success "Development deployment started"
    print_info "Backend: http://localhost:8000"
    print_info "Ollama: http://localhost:11434"

    print_info "Waiting for services to be ready..."
    sleep 5

    print_info "Checking service health..."
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend is healthy!"
    else
        print_error "Backend is not responding"
    fi

    print_info "Next steps:"
    echo "  1. Pull Ollama model: ./deploy.sh pull-model"
    echo "  2. View logs: ./deploy.sh logs"
    echo "  3. Test API: curl http://localhost:8000/health"
}

deploy_prod() {
    print_info "Starting production deployment..."

    check_dependencies
    setup_env

    print_info "Building production images (this may take a while)..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    print_info "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d

    print_success "Production deployment started"
    print_info "Backend: http://localhost:8000 (or your configured port)"

    print_info "Waiting for services to be ready..."
    sleep 10

    print_info "Checking service health..."
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend is healthy!"
    else
        print_error "Backend is not responding. Check logs: ./deploy.sh logs"
    fi

    print_info "Next steps:"
    echo "  1. Pull Ollama model: ./deploy.sh pull-model"
    echo "  2. Setup reverse proxy (see DEPLOYMENT.md)"
    echo "  3. Configure SSL/HTTPS"
    echo "  4. Monitor logs: ./deploy.sh logs"
}

stop_services() {
    print_info "Stopping services..."

    if [ -f docker-compose.prod.yml ]; then
        docker-compose -f docker-compose.prod.yml down
    fi

    docker-compose down

    print_success "Services stopped"
}

view_logs() {
    print_info "Viewing logs (Ctrl+C to exit)..."

    if docker ps | grep -q "mini-agi-backend-prod"; then
        docker-compose -f docker-compose.prod.yml logs -f
    else
        docker-compose logs -f
    fi
}

pull_model() {
    print_info "Pulling Ollama model..."

    # Get model from .env or use default
    if [ -f .env ]; then
        MODEL=$(grep LLM_MODEL .env | cut -d '=' -f2 | tr -d ' ')
    else
        MODEL="llama3.1:8b"
    fi

    print_info "Model: $MODEL"

    # Determine container name
    if docker ps | grep -q "ollama-prod"; then
        CONTAINER="ollama-prod"
    else
        CONTAINER="ollama"
    fi

    print_info "Container: $CONTAINER"

    if ! docker ps | grep -q "$CONTAINER"; then
        print_error "Ollama container is not running. Start it first: ./deploy.sh dev"
        exit 1
    fi

    docker exec -it $CONTAINER ollama pull $MODEL

    print_success "Model pulled successfully"
    print_info "Available models:"
    docker exec -it $CONTAINER ollama list
}

show_status() {
    print_info "Service Status:"
    echo ""
    docker-compose ps
    echo ""
    print_info "Container Stats:"
    docker stats --no-stream
}

show_help() {
    echo "Mini-AGI Backend Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  dev          Start development deployment"
    echo "  prod         Start production deployment"
    echo "  stop         Stop all services"
    echo "  logs         View service logs"
    echo "  pull-model   Pull Ollama model"
    echo "  status       Show service status"
    echo "  help         Show this help message"
    echo ""
}

# Main script
case "$1" in
    dev)
        deploy_dev
        ;;
    prod)
        deploy_prod
        ;;
    stop)
        stop_services
        ;;
    logs)
        view_logs
        ;;
    pull-model)
        pull_model
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
