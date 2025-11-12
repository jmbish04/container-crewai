/**
 * Cloudflare Worker for GitHub Resume Generator Container
 *
 * This Worker manages routing between the Cloudflare edge and the
 * containerized FastAPI application running the CrewAI resume generator.
 */

import { Container, getContainer } from "@cloudflare/containers";

/**
 * Container class that manages the lifecycle of the Resume Generator container
 */
export class ResumeGeneratorContainer extends Container {
  // FastAPI app runs on port 8080 (matching the Dockerfile)
  defaultPort = 8080;

  // Stop the container after 10 minutes of inactivity to save resources
  sleepAfter = "10m";

  /**
   * Initialize the container with environment variables
   */
  constructor(state, env) {
    super(state, env);

    // Pass secrets to the container as environment variables
    this.envVars = {
      GEMINI_API_KEY: env.GEMINI_API_KEY || "",
      LINKEDIN_USERNAME: env.LINKEDIN_USERNAME || "",
      LINKEDIN_PASSWORD: env.LINKEDIN_PASSWORD || "",
      PORT: "8080"
    };
  }

  /**
   * Lifecycle hook: called when container starts
   */
  onStart() {
    console.log("Resume Generator container started successfully");
  }

  /**
   * Lifecycle hook: called when container stops
   */
  onStop() {
    console.log("Resume Generator container stopped");
  }

  /**
   * Lifecycle hook: called on container errors
   */
  onError(error) {
    console.error("Resume Generator container error:", error);
  }
}

/**
 * Main request handler for the Worker
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // Get or create container instance
    // Using "main" as the instance ID - all requests use the same container
    const container = getContainer(env.RESUME_CONTAINER, "main");

    try {
      // Route all requests to the container
      // The FastAPI app handles:
      // - GET / -> serves the static HTML page
      // - GET /resume?username=X -> streams resume generation
      // - GET /r/* -> serves static assets (CSS, images, etc.)

      // Forward the request to the container
      const containerRequest = new Request(url.toString(), {
        method: request.method,
        headers: request.headers,
        body: request.body,
      });

      const response = await container.fetch(containerRequest);

      // Add CORS headers if needed
      const newHeaders = new Headers(response.headers);
      // TODO: Restrict this to your frontend's domain in production.
      newHeaders.set("Access-Control-Allow-Origin", "https://your-frontend.com");
      newHeaders.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      newHeaders.set("Access-Control-Allow-Headers", "Content-Type");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });

    } catch (error) {
      console.error("Worker error:", error);

      return new Response(
        JSON.stringify({
          error: "Container unavailable",
          message: error.message,
          details: "The resume generator container is currently unavailable. Please try again in a moment."
        }),
        {
          status: 503,
          headers: {
            "Content-Type": "application/json",
            "Retry-After": "10"
          }
        }
      );
    }
  },
};
