// ApiService.cs

using System.Text;
using Newtonsoft.Json;
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;

namespace App
{
    // Define C# records to match the JSON structure from the API
    public record ChatRequest(string message, string thread_id);
    public record StreamedResponse(string type, string content, string tool, string output, string thread_id);

    public class ApiService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseAddress;

        public ApiService()
        {
            _httpClient = new HttpClient();
            // Set a timeout to prevent the app from hanging indefinitely
            _httpClient.Timeout = System.Threading.Timeout.InfiniteTimeSpan;

            // Select the correct base address based on the platform
            _baseAddress = GetBaseAddress();
        }

        private string GetBaseAddress()
        {
            // This logic correctly handles the different network environments
            // for local development.
#if ANDROID
            return "http://10.0.2.2:8000";
#elif IOS
            return "http://localhost:8000";
#else // Windows, MacCatalyst, etc.
            return "http://localhost:8000";
#endif
        }

        public async IAsyncEnumerable<StreamedResponse> StreamChatResponseAsync(string message, string threadId)
        {
            var requestUrl = $"{_baseAddress}/chat";
            var chatRequest = new ChatRequest(message, threadId);
            var jsonPayload = JsonConvert.SerializeObject(chatRequest);
            var content = new StringContent(jsonPayload, Encoding.UTF8, new System.Net.Http.Headers.MediaTypeHeaderValue("application/json"));

            using var request = new HttpRequestMessage(HttpMethod.Post, requestUrl) { Content = content };

            // Use HttpCompletionOption.ResponseHeadersRead to start processing the response
            // as soon as the headers are received, without waiting for the full body.
            using var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);

            response.EnsureSuccessStatusCode();

            using var stream = await response.Content.ReadAsStreamAsync();
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream)
            {
                var line = await reader.ReadLineAsync();

                // The server sends data in the format "data: {json_payload}"
                if (string.IsNullOrWhiteSpace(line) || !line.StartsWith("data:"))
                {
                    continue;
                }

                var jsonData = line.Substring(5).Trim();
                var streamedResponse = JsonConvert.DeserializeObject<StreamedResponse>(jsonData);

                if (streamedResponse != null)
                {
                    yield return streamedResponse;
                    if (streamedResponse.type == "stream_end")
                    {
                        yield break; // Stop iterating once the stream is finished
                    }
                }
            }
        }
    }
}