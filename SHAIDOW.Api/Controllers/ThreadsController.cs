using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SHAIDOW.Api.Data;

namespace SHAIDOW.Api.Controllers;

public record ThreadSummary(Guid Id, string Title, DateTime LastMessageAt);
public record MessageDto(Guid Id, string Author, string Text, string? ImageUrl, DateTime CreatedAt);

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ThreadsController : ControllerBase
{
    private readonly AppDbContext _db;
    public ThreadsController(AppDbContext db) => _db = db;

    private Guid CurrentUserId =>
        Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.FindFirstValue("sub")!);

    [HttpGet]
    public async Task<ActionResult<List<ThreadSummary>>> GetThreads()
    {
        var threads = await _db.Threads
            .Where(t => t.UserId == CurrentUserId)
            .OrderByDescending(t => t.LastMessageAt)
            .Select(t => new ThreadSummary(t.Id, t.Title, t.LastMessageAt))
            .ToListAsync();

        return Ok(threads);
    }

    [HttpGet("{id}/messages")]
    public async Task<ActionResult<List<MessageDto>>> GetMessages(Guid id)
    {
        var owns = await _db.Threads.AnyAsync(t => t.Id == id && t.UserId == CurrentUserId);
        if (!owns) return NotFound();

        var messages = await _db.Messages
            .Where(m => m.ThreadId == id)
            .OrderBy(m => m.CreatedAt)
            .Select(m => new MessageDto(m.Id, m.Author, m.Text, m.ImageUrl, m.CreatedAt))
            .ToListAsync();

        return Ok(messages);
    }

    [HttpGet("/api/images")]
    public async Task<ActionResult<List<String>>> GetMyImages()
    {
        var urls = await _db.Messages
            .Where(m => m.ImageUrl != null && m.Thread!.UserId == CurrentUserId)
            .OrderByDescending(m => m.CreatedAt)
            .Select(m => m.ImageUrl)
                .ToListAsync();
        return Ok(urls);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteThread(Guid id)
    {
        var thread = await _db.Threads.FirstOrDefaultAsync(t => t.Id == id && t.UserId == CurrentUserId);
        if (thread is null) return NotFound();

        _db.Threads.Remove(thread); // cascade delete removes its Messages too, per the FK config in AppDbContext
        await _db.SaveChangesAsync();
        return NoContent();
    }
}
