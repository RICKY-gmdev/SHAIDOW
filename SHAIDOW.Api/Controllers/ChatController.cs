using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SHAIDOW.Api.Data;
using SHAIDOW.Api.Data.Entities;
using SHAIDOW.Api.Services;

namespace SHAIDOW.Api.Controllers;

public record ChatRequest(string Message, Guid? ThreadId);

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ChatController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly AgentBackendClient _agent;

    public ChatController(AppDbContext db, AgentBackendClient agent)
    {
        _db = db;
        _agent = agent;
    }

    [HttpPost]
    public async Task Chat(ChatRequest req, CancellationToken ct)
    {
        var userId = Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")!);

        var thread = req.ThreadId is not null
            ? await _db.Threads.FirstOrDefaultAsync(t => t.Id == req.ThreadId && t.UserId == userId, ct)
            : null;

        if (thread is null)
        {
            thread = new ChatThread
            {
                UserId = userId,
                Title = req.Message.Length > 50 ? req.Message[..50] + "..." : req.Message
            };
            _db.Threads.Add(thread);
        }

        _db.Messages.Add(new ChatMessage { ThreadId = thread.Id, Author = "user", Text = req.Message });
        thread.LastMessageAt = DateTime.UtcNow;
        await _db.SaveChangesAsync(ct);

        Response.Headers.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";

        // The Python backend's LangGraph checkpointer is keyed by thread_id - reuse the same
        // GUID so the agent keeps its own conversational memory in sync with our Postgres thread.
        var pythonStream = await _agent.StreamChatAsync(req.Message, thread.Id.ToString(), ct);
        using var reader = new StreamReader(pythonStream);

        var assistantText = new StringBuilder();
        string? capturedImageUrl = null;

        while (!reader.EndOfStream && !ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct);
            if (string.IsNullOrWhiteSpace(line) || !line.StartsWith("data:")) continue;

            // Forward every line to the client immediately - Angular sees the same stream MAUI used to.
            await Response.WriteAsync(line + "\n\n", ct);
            await Response.Body.FlushAsync(ct);

            var json = line["data:".Length..].Trim();
            using var doc = JsonDocument.Parse(json);
            var type = doc.RootElement.GetProperty("type").GetString();

            if (type == "text_chunk")
            {
                assistantText.Append(doc.RootElement.GetProperty("content").GetString());
            }
            else if (type == "tool_end" && doc.RootElement.TryGetProperty("output", out var output))
            {
                var outputStr = output.GetString() ?? "";
                const string prefix = "IMAGE_URL::";
                var idx = outputStr.IndexOf(prefix, StringComparison.Ordinal);
                if (idx != -1) capturedImageUrl = outputStr[(idx + prefix.Length)..].Trim('\'', '"');
            }
        }

        // Persist the assistant's full reply now that streaming is done.
        _db.Messages.Add(new ChatMessage
        {
            ThreadId = thread.Id,
            Author = "assistant",
            Text = assistantText.ToString(),
            ImageUrl = capturedImageUrl
        });
        thread.LastMessageAt = DateTime.UtcNow;
        await _db.SaveChangesAsync(ct);
    }
}
