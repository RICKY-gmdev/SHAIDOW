// ApiService.cs (with debugging)

using System.Text;
using Newtonsoft.Json;
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;
using System.Diagnostics; // Required for Debug.WriteLine

namespace App
{
    public record ChatRequest(string message, string? thread_id);

    public class StreamedResponse
    {
        [JsonProperty("type")]
        public string? Type { get; set; }

        [JsonProperty("content")]
        public string? Content { get; set; }

        [JsonProperty("tool")]
        public string? Tool { get; set; }

        [JsonProperty("output")]
        public string? Output { get; set; }

        [JsonProperty("thread_id")]
        public string? ThreadId { get; set; }
    }

    public class ApiService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseAddress;

        public ApiService()
        {
            _httpClient = new HttpClient();
            // Set a finite timeout for debugging to prevent infinite hangs
            _httpClient.Timeout = TimeSpan.FromSeconds(30);
            _baseAddress = GetBaseAddress();
        }

        private string GetBaseAddress()
        {
            return "https://shaidow-backend-production.up.railway.app";
        }

        public async IAsyncEnumerable<StreamedResponse> StreamChatResponseAsync(string message, string? threadId)
        {
            var requestUrl = $"{_baseAddress}/chat";
            Debug.WriteLine($"[ApiService] Preparing to send request to: {requestUrl}");

            var chatRequest = new ChatRequest(message, threadId);
            var jsonPayload = JsonConvert.SerializeObject(chatRequest);
            var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            using var request = new HttpRequestMessage(HttpMethod.Post, requestUrl) { Content = content };

            HttpResponseMessage response = null;
            StreamedResponse? errorResponse = null;
            try
            {
                Debug.WriteLine("[ApiService] Sending HTTP request...");
                response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
                Debug.WriteLine($"[ApiService] Received response with status code: {response.StatusCode}");
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                // This is the most important log. It will tell us why the connection failed.
                Debug.WriteLine($"[ApiService] HTTP REQUEST FAILED: {ex.Message}");
                Debug.WriteLine($"[ApiService] Base exception: {ex.InnerException?.Message}");
                // Prepare a custom error to be displayed in the UI
                errorResponse = new StreamedResponse { Type = "error", Content = $"Connection to the backend failed. Is the server running? Error: {ex.Message}" };
            }
            catch (TaskCanceledException ex)
            {
                Debug.WriteLine($"[ApiService] HTTP REQUEST TIMED OUT: {ex.Message}");
                errorResponse = new StreamedResponse { Type = "error", Content = "Connection to the backend timed out." };
            }

            if (errorResponse != null)
            {
                yield return errorResponse;
                yield break;
            }


            using var stream = await response.Content.ReadAsStreamAsync();
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream)
            {
                var line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line) || !line.StartsWith("data:"))
                {
                    continue;
                }

                var jsonData = line.Substring(5).Trim();
                var streamedResponse = JsonConvert.DeserializeObject<StreamedResponse>(jsonData);

                if (streamedResponse != null)
                {
                    yield return streamedResponse;
                    if (streamedResponse.Type == "stream_end")
                    {
                        yield break;
                    }
                }
            }
        }
    }
}