using Microsoft.Maui.Controls;
using Microsoft.Maui.Storage;
using System;
using System.Collections.ObjectModel;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Text;
using System.Threading.Tasks;
using System.Net;
using System.Net.Http.Headers;
using Microsoft.Maui.Controls.PlatformConfiguration.TizenSpecific;
using Shaidow.Data;
using MauiPopup.Views;



namespace App
{
    public partial class MainPage : ContentPage
    {
        public class ChatMessage
        {
            public string Text { get; set; } = "";
            public string ImageUrl { get; set; } = "";
            public bool IsText => !string.IsNullOrEmpty(Text);
            public bool IsImage => !string.IsNullOrEmpty(ImageUrl);
        }

        ObservableCollection<ChatMessage> chatMessages = new ObservableCollection<ChatMessage>();
        private readonly HttpClient httpClient = new HttpClient();

        private readonly string mistralApiUrl = "https://api.mistral-7b.com/v1/chat/completions";

        private readonly string claudeApiUrl = "https://api.anthropic.com/v1/messages";
        private readonly string geminiApiUrl = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key=AIzaSyCY630oJvwNHgE_fmN-ab9UKyI4A5oXi_c";
        private bool Isresponding = false;

        static Dictionary<string, int> CategoryMap = new Dictionary<string, int>()
        {
            {"Information Seeking", 1},
            {"Image Generation", 2},
            {"Report Writing", 3}
        };

        static Dictionary<int, Func<string, Task<string>>> routeHandler;

        public MainPage()
        {
            InitializeComponent();
            ChatList.ItemsSource = chatMessages;

            routeHandler = new Dictionary<int, Func<string, Task<string>>>()
            {
                {1, HandleInfoQuery},
                {2, HandleImgQuery},
                {3, HandleCreativeQuery}
            };
            Microsoft.Maui.Controls.Application.Current.UserAppTheme = AppTheme.Dark;
            Preferences.Set("AppTheme", "Dark");
        }

        public async void UpdateLoadingIndicator()
        {
            if (Isresponding)
            {
                Spinner.IsVisible = true;
                Spinner.IsRunning = true;
                await Spinner.TranslateTo(23, 0, 400, Easing.SinOut);
            }
            else
            {
                await Spinner.TranslateTo(0, 0, 400, Easing.SinIn);
                Spinner.IsVisible = false;
                Spinner.IsRunning = false;
                Spinner.TranslationX = 0;
            }
        }

        private void OnLightModeClicked(object sender, EventArgs e)
        {
            if (Microsoft.Maui.Controls.Application.Current.UserAppTheme == AppTheme.Dark)
            {
                Microsoft.Maui.Controls.Application.Current.UserAppTheme = AppTheme.Light;
                Preferences.Set("AppTheme", "Light");
            }
            else
            {
                Microsoft.Maui.Controls.Application.Current.UserAppTheme = AppTheme.Dark;
                Preferences.Set("AppTheme", "Dark");
            }
        }

        private async void OnSendMessage(object sender, EventArgs e)
        {
            string userMessage = (UserInput.Text ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(userMessage))
            {
                chatMessages.Add(new ChatMessage { Text = "Come on, type something!" });
                return;
            }

            chatMessages.Add(new ChatMessage { Text = "You: " + userMessage });
            UserInput.Text = "";
            string category = await GetResponseCategory(userMessage);

            if (CategoryMap.TryGetValue(category, out int categoryId) && routeHandler.TryGetValue(categoryId, out var handler))
            {
                string response = await handler(userMessage);
                if (categoryId == 2)
                {
                    if (!string.IsNullOrEmpty(response))
                    {
                        if (Uri.IsWellFormedUriString(response, UriKind.Absolute))
                            chatMessages.Add(new ChatMessage { ImageUrl = response });

                    }
                }
                else
                {
                    chatMessages.Add(new ChatMessage { Text = "SHAIDOW AI: " + response });
                }
            }
            else
            {
                string geminiResponse = await HandleFallbackQuery(userMessage);
                chatMessages.Add(new ChatMessage { Text = "SHAIDOW AI: " + geminiResponse });
            }
        }

        private async Task<string> GetResponseCategory(string userMessage)
        {
            try
            {
                var requestBody = new
                {
                    model = "mistral-small",
                    messages = new[]
                    {
                        new { role = "user", content = $"Classify the following user query into one of these categories: 'Information Seeking', 'Image Generation', or 'Report Writing'.\n\nQuery: {userMessage}" }
                    }
                };

                string jsonBody = JsonSerializer.Serialize(requestBody);
                var request = new HttpRequestMessage(HttpMethod.Post, mistralApiUrl)
                {
                    Content = new StringContent(jsonBody, Encoding.UTF8, "application/json")
                };
                request.Headers.Add("Authorization", "Bearer wjy20ymt9gFt4EMgvD4ymjxpeMun1cVD");

                var response = await httpClient.SendAsync(request);
                if (!response.IsSuccessStatusCode)
                {
                    Console.WriteLine($"Mistral categorization error : {response.StatusCode}, Details : {await response.Content.ReadAsStringAsync()}");
                    return "Unknown";
                }

                var responseBody = await response.Content.ReadAsStringAsync();
                using var jsonDoc = JsonDocument.Parse(responseBody);
                string rawCategory = jsonDoc.RootElement
                    .GetProperty("choices")[0]
                    .GetProperty("message")
                    .GetProperty("content")
                    .GetString()?.Trim() ?? "Unknown";

                return CategoryMap.ContainsKey(rawCategory) ? rawCategory : "Unknown";
            }
            catch (Exception)
            {
                return "Unknown";
            }
        }

        private async Task<string> HandleFallbackQuery(string query)
        {
            Isresponding = true;
            UpdateLoadingIndicator();
            try
            {
                var requestBody = new
                {
                    contents = new[]
                    {
                        new
                        {
                            parts = new[]
                            {
                                new { text = query },
                                new { text = $"The user asked: {query}. Respond to this query as a helpful and informative AI assistant.This application is shaidow make it your identity for now It brings different high level models in one place to help user get the best possible response possible in the market,It is second year student's curios project designed to be a versatile chatbot, capable of understanding and responding to a variety of user queries. It's built with the goal of providing helpful information, generating images, and assisting with creative writing tasks.The app works by taking a user's text input and then using AI to provide a relevant response.  The app first sends the user's query to the Mistral AI to determine the category of the request. If Mistral is unable to categorize the user's query, or if the primary AI model for a specific category fails to provide a valid response, or if a primary API returns an empty or invalid response, this fallback system is activated.When the fallback system is activated, the user's query is sent to you. Please provide a general, helpful, and informative text-based response to the user's query. If you cannot answer, say you do not know. The application is designed for general-purpose use and is not intended for any specific high-risk applications. This app is intended for educational and demonstration purposes." }
                            }
                        }
                    }
                };

                string jsonBody = JsonSerializer.Serialize(requestBody);
                var request = new HttpRequestMessage(HttpMethod.Post, geminiApiUrl)
                {
                    Content = new StringContent(jsonBody, Encoding.UTF8, "application/json")
                };

                var response = await httpClient.SendAsync(request);
                if (!response.IsSuccessStatusCode)
                    return $"Gemini API Error: {response.StatusCode}";

                var responseBody = await response.Content.ReadAsStringAsync();
                using var jsonDoc = JsonDocument.Parse(responseBody);

                if (jsonDoc.RootElement.TryGetProperty("candidates", out var candidates) &&
                    candidates.GetArrayLength() > 0 &&
                    candidates[0].TryGetProperty("content", out var content) &&
                    content.TryGetProperty("parts", out var parts) &&
                    parts.GetArrayLength() > 0 &&
                    parts[0].TryGetProperty("text", out var text))
                {
                    return text.GetString() ?? "Gemini gave empty response.";
                }

                return "Gemini returned an unexpected format.";
            }
            catch (Exception ex)
            {
                return $"Error: {ex.Message}";
            }
            finally
            {
                Isresponding = false;
                UpdateLoadingIndicator();
            }
        }

        private async Task<string> HandleInfoQuery(string query)
        {
            Isresponding = true;
            UpdateLoadingIndicator();
            try
            {
                var requestBody = new
                {
                    model = "mistral-small",
                    messages = new[]
                    {
                new { role = "system", content = "You are SHAIDOW, a powerful AI assistant using multiple free models. You are not Mistral. Only introduce yourself if asked." },
                new { role = "user", content = query }
            }
                };

                string jsonBody = JsonSerializer.Serialize(requestBody);
                var request = new HttpRequestMessage(HttpMethod.Post, mistralApiUrl)
                {
                    Content = new StringContent(jsonBody, Encoding.UTF8, "application/json")
                };
                request.Headers.Add("Authorization", "Bearer wjy20ymt9gFt4EMgvD4ymjxpeMun1cVD");

                var response = await httpClient.SendAsync(request);
                if (!response.IsSuccessStatusCode)
                    return $"Mistral Info Query Error: {response.StatusCode}";

                var responseBody = await response.Content.ReadAsStringAsync();
                using var jsonDoc = JsonDocument.Parse(responseBody);
                var text = jsonDoc.RootElement
                    .GetProperty("choices")[0]
                    .GetProperty("message")
                    .GetProperty("content")
                    .GetString();

                return text ?? "SHAIDOW couldn't generate a proper response.";
            }
            catch (Exception ex)
            {
                return $"Info Query Error: {ex.Message}";
            }
            finally
            {
                Isresponding = false;
                UpdateLoadingIndicator();
            }
        }



        private async Task<string> HandleImgQuery(string query)
        {
            Isresponding = true;
            UpdateLoadingIndicator();
            //await popupservice.ShowPopupAsync(new ImagePopup(), "Generating Image...");

            try
            {
                using var client = new HttpClient();
                client.DefaultRequestHeaders.Add("api-key", "b2d062a1-97a0-4d77-9db9-f63bcb9cbe3c");

                var content = new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    { "text", query }
                });

                var response = await client.PostAsync("https://github.com/RICKY-gmdev/SHAIDOW/blob/main/App/Resources/Images/79177df4-99c8-441a-88aa-1181b7b07f89.png?raw=true", content);
                var responseString = await response.Content.ReadAsStringAsync();

                if (!response.IsSuccessStatusCode)
                {
                    return $"Image Generation Error: {response.StatusCode}";
                }

                var json = JsonDocument.Parse(responseString);
                if (json.RootElement.TryGetProperty("output_url", out var imageUrlElement))
                {
                    return imageUrlElement.GetString();
                }

                return "Image generation failed: output_url missing.";
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error in HandleImgQuery: {ex.Message}");
                return await HandleFallbackQuery(query);
            }
            finally
            {
                Isresponding = false;
                UpdateLoadingIndicator();
            }

        }




        private async Task<string> HandleCreativeQuery(string query)
        {
            Isresponding = true;
            UpdateLoadingIndicator();
            try
            {
                // Add your Claude or other logic here later
                return await HandleFallbackQuery(query);
            }
            finally
            {
                Isresponding = false;
                UpdateLoadingIndicator();
            }
        }
    }
}
