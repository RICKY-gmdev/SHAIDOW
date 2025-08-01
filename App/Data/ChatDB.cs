
using SQLite;
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;

namespace Shaidow.Services
{
    public class ChatDatabase
    {   public class ChatHistory
    {
        [PrimaryKey, AutoIncrement]
        public int Id { get; set; }
        public string Sender { get; set; } = String.Empty;
        public string MessageText { get; set; } = String.Empty;
        public DateTime Timestamp { get; set; }
    }

        private readonly SQLiteAsyncConnection _database;

        public ChatDatabase(string dbPath)
        {
            _database = new SQLiteAsyncConnection(dbPath);
            _database.CreateTableAsync<ChatHistory>().Wait();
        }

        public Task<List<ChatHistory>> GetAllMessagesAsync() =>
            _database.Table<ChatHistory>().OrderBy(x => x.Timestamp).ToListAsync();

        public Task<int> SaveMessageAsync(ChatHistory message) =>
            _database.InsertAsync(message);

        public Task<int> ClearHistoryAsync() =>
            _database.DeleteAllAsync<ChatHistory>();
    }
}
