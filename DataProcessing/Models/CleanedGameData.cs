// DataProcessing/Models/CleanedGameData.cs
namespace Static_Football_Rankings.DataProcessing.Models
{
    public class CleanedGameData
    {
        public DateTime GameDate { get; set; }
        public int Season { get; set; }
        public string HomeTeam { get; set; }
        public string VisitorTeam { get; set; }
        public bool IsNeutral { get; set; }
        public string Location { get; set; }
        public string Location2 { get; set; }  // For future use
        public int? Line { get; set; }         // Nullable
        public bool FutureGame { get; set; }
        public string Source { get; set; }
        public DateTime DateAdded { get; set; }
        public int? OT { get; set; }           // Nullable
        public bool Forfeit { get; set; }
        public int? VisitorScore { get; set; } // Nullable
        public int? HomeScore { get; set; }    // Nullable
        public int? Margin { get; set; }       // Nullable
        public int? AccessId { get; set; }     // Nullable
    }
}