//API SERVICEpip install tavily-python
using System.Text;
using Newtonsoft.Json;
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Runtime.CompilerServices;

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
            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(30)
            };
            _baseAddress = "http://127.0.0.1:8000";
        }

        public async IAsyncEnumerable<StreamedResponse> StreamChatResponseAsync(
            string message,
            string? threadId,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            var requestUrl = $"{_baseAddress}/chat";
            Debug.WriteLine($"[ApiService] Sending request to: {requestUrl}");

            var chatRequest = new ChatRequest(message, threadId);
            var jsonPayload = JsonConvert.SerializeObject(chatRequest);
            var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            using var request = new HttpRequestMessage(HttpMethod.Post, requestUrl) { Content = content };

            HttpResponseMessage? response = null;
            string? errorContent = null;
            try
            {
                response = await _httpClient.SendAsync(
                    request,
                    HttpCompletionOption.ResponseHeadersRead,
                    cancellationToken
                );
                Debug.WriteLine($"[ApiService] Status: {response.StatusCode}");
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                errorContent = $"Connection failed: {ex.Message}";
            }
            catch (TaskCanceledException)
            {
                errorContent = "Request timed out or cancelled.";
            }

            if (errorContent != null)
            {
                yield return new StreamedResponse { Type = "error", Content = errorContent };
                yield break;
            }

            if (response == null)
            {
                yield return new StreamedResponse { Type = "error", Content = "No response received from server." };
                yield break;
            }

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream && !cancellationToken.IsCancellationRequested)
            {
                var line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line) || !line.StartsWith("data:"))
                    continue;

                var jsonData = line.Substring(5).Trim();
                var streamedResponse = JsonConvert.DeserializeObject<StreamedResponse>(jsonData);

                if (streamedResponse != null)
                {
                    yield return streamedResponse;
                    if (streamedResponse.Type == "stream_end")
                        yield break;
                }
            }
        }
    }
}
