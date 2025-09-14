using System.Globalization;
using Markdig;
using Microsoft.Maui.Controls;

namespace App.Converters
{
    public class MarkdownToHtmlConverter : IValueConverter
    {
        public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            if (value is not string markdownText)
                return new HtmlWebViewSource { Html = "<html><body></body></html>" };

            // Convert the Markdown string to an HTML string
            var htmlText = Markdown.ToHtml(markdownText ?? "");

            // Create a full HTML document with styling for our dark theme.
            // This is crucial for making the text white and the background transparent.
            var htmlSource = new HtmlWebViewSource
            {
                Html = $@"
                    <html>
                        <head>
                            <style>
                                body {{ 
                                    background-color: transparent; 
                                    color: white; 
                                    font-family: sans-serif; 
                                    font-size: 14px;
                                    word-wrap: break-word;
                                }}
                                a {{ color: #58A6FF; }} /* Style for links */
                                h1, h2, h3 {{ margin-bottom: -10px; }}
                                li {{ margin-bottom: 5px; }}
                            </style>
                        </head>
                        <body>
                            {htmlText}
                        </body>
                    </html>"
            };

            return htmlSource;
        }

        public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}