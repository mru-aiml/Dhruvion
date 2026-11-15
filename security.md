# DHRUVION --- Security and Safety Considerations

## 1. Scope

DHRUVION is a hackathon prototype that may run locally or be deployed
for judging. It is not a certified aerospace system. Security controls
protect the application, user inputs, data files, API, and model-tool
boundary. Safety-related language must remain conservative: the product
provides estimates and decision support, not guarantees of safe
traversal.

## 2. Security principles

-   Minimize exposed functionality and privileges.
-   Validate all external input at the API boundary.
-   Treat user text, NASA metadata, downloaded files, and model output
    as untrusted.
-   Keep secrets out of source control and logs.
-   Keep LLM tools allowlisted and narrowly scoped.
-   Preserve data provenance and uncertainty.
-   Fail closed when required data or safety assumptions are missing.

## 3. Secrets and configuration

-   Store credentials and API keys in environment variables or a secret
    manager.
-   Provide `.env.example` with placeholder names only.
-   Add `.env`, private keys, tokens, and credential files to
    `.gitignore`.
-   Never expose backend secrets through frontend `VITE_` variables.
-   Rotate any credential accidentally committed or shared.
-   Use separate development and deployment credentials.
-   Do not place NASA service keys or hosted-model keys in client-side
    code.

## 4. API security

-   Validate request bodies, query parameters, identifiers, coordinates,
    numeric ranges, and payload sizes using Pydantic.
-   Restrict CORS to known frontend origins in deployed environments.
-   Apply rate limits to expensive endpoints and assistant requests
    where feasible.
-   Set timeouts for raster processing, external data access, and model
    calls.
-   Return generic client errors; keep stack traces in server logs only.
-   Avoid arbitrary file paths supplied by clients.
-   Resolve dataset IDs through a server-side catalog rather than
    accepting arbitrary filesystem paths.
-   Use HTTPS in deployed environments.
-   If authentication is introduced, enforce authorization on every
    protected resource; do not rely on hidden UI controls.

## 5. File and dataset safety

-   Treat downloaded archives, rasters, vectors, and metadata as
    untrusted input.
-   Restrict accepted formats and enforce file size limits.
-   Avoid extracting archives without path traversal protection.
-   Store uploaded/processed files outside executable web roots.
-   Use generated filenames or catalog IDs rather than trusting client
    filenames.
-   Validate raster dimensions, band count, CRS metadata, nodata, and
    bounds before processing.
-   Avoid unsafe deserialization formats such as untrusted pickle files.
-   Keep raw NASA source files immutable and separate from processed
    outputs.
-   Record checksums for important source artifacts where practical.

## 6. LLM and tool security

The assistant is a potential prompt-injection boundary. Retrieved
metadata, target descriptions, user messages, and external documents can
contain adversarial instructions.

Controls: - Treat all retrieved content as data, never as tool policy. -
Define a fixed allowlist of tools and strict Pydantic argument
schemas. - Do not provide shell, Python execution, arbitrary SQL,
unrestricted HTTP, or unrestricted filesystem tools. - Enforce
authorization and validation in the tool implementation, not in the
prompt alone. - Limit tool call count, execution time, and returned
payload size. - Do not allow the model to change mission constraints or
overwrite source data. - Validate model output before returning it to
the frontend. - Escape/sanitize rendered Markdown or HTML to prevent
XSS. - Keep tool activity logs aligned with actual execution. - If a
tool fails, report failure; do not let the model infer a successful
result. - Do not use model-generated confidence as a calibrated
probability.

## 7. Frontend security

-   Render untrusted text as text, not raw HTML.
-   Sanitize any Markdown/HTML rendering.
-   Avoid `dangerouslySetInnerHTML` unless strictly necessary and
    sanitized.
-   Do not store sensitive tokens in local storage if avoidable.
-   Keep dependencies minimal and update vulnerable packages.
-   Validate URLs before making them clickable.
-   Do not trust values received from the browser; backend revalidates
    all mission inputs.
-   Avoid leaking internal error details in toast messages.

## 8. Mission-safety and data-integrity safeguards

-   Display `OBSERVED`, `DERIVED`, `SIMULATED`, `UNAVAILABLE`, and
    `UNVERIFIED` states distinctly.
-   Never describe a calculated route as guaranteed safe.
-   Use wording such as "lowest estimated terrain risk under the
    configured model."
-   Missing terrain data must not be interpreted as low risk.
-   A missing return route or missing required time input must yield
    `UNVERIFIED`, not `FEASIBLE`.
-   Show the assumptions behind speed, exploration duration, reserve
    time, and route costs.
-   Clearly mark simulated emergency events and demo telemetry.
-   Keep scientific observations distinct from interpretations.
-   Do not imply NASA endorsement, certification, or live mission
    integration.

## 9. Logging and privacy

-   Log request IDs, endpoint, status, duration, and safe diagnostic
    context.
-   Do not log API keys, access tokens, passwords, or unnecessary
    personal data.
-   Avoid storing full assistant conversations unless required for the
    demo.
-   If conversations are persisted, define retention and deletion
    behavior.
-   Restrict access to logs and database files in deployment.

## 10. Deployment checklist

-   [ ] No secrets in Git history or frontend bundle.
-   [ ] `.env` is ignored and `.env.example` contains placeholders only.
-   [ ] CORS is restricted.
-   [ ] HTTPS is enabled for public deployment.
-   [ ] API validates inputs and payload sizes.
-   [ ] Dataset paths cannot be controlled by untrusted clients.
-   [ ] LLM tools are allowlisted and schema-validated.
-   [ ] Errors do not reveal stack traces or secrets.
-   [ ] Dependencies are reviewed.
-   [ ] Simulated data and limitations are visible.
-   [ ] The product is labelled as a prototype and not a certified
    safety system.
