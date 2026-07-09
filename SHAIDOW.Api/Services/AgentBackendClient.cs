namespace SHAIDOW.Api.Services;

// Thin wrapper around the Python FastAPI backend. It has no idea users/auth/DB exist -
// it just takes a message + thread_id and streams SSE lines back. That separation is intentional.
public class AgentBackendClient
{
    private readonly HttpClient _http;

    public AgentBackendClient(HttpClient http, IConfiguration config)
    {
        _http = http;
        _http.BaseAddress = new Uri(config["AgentBackend:BaseUrl"] ?? "http://127.0.0.1:8000");
        _http.Timeout = Timeout.InfiniteTimeSpan; // streaming responses can run long
    }

    // Returns the raw stream so the controller can forward each line to the client as it arrives.
    public async Task<Stream> StreamChatAsync(string message, string? threadId, CancellationToken ct)
    {
        var payload = new { message, thread_id = threadId };
        var request = new HttpRequestMessage(HttpMethod.Post, "/chat")
        {
            Content = JsonContent.Create(payload)
        };

        var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStreamAsync(ct);
    }
}
