// DataProcessing/Cleaners/GameDataCleaner.cs
using Static_Football_Rankings.DataProcessing.Models;
using System;
using System.Collections.Generic;

namespace Static_Football_Rankings.DataProcessing.Cleaners
{
    public class GameDataCleaner
    {
        private readonly int _season;

        public GameDataCleaner(int season)
        {
            _season = season;
        }

        public CleanedGameData CleanGameData(Dictionary<string, string> rawData)
        {
            try
            {
                var cleaned = new CleanedGameData
                {
                    Season = _season,
                    DateAdded = DateTime.Parse(rawData["ScrapedAt"].Trim()),
                    Source = rawData["URL"].Trim(),
                    FutureGame = false,  // This is for current scores import
                    Forfeit = false      // Default unless we detect otherwise
                };

                // Parse the date
                cleaned.GameDate = ParseGameDate(rawData["Date"], _season);

                // Determine teams and location
                (cleaned.HomeTeam, cleaned.VisitorTeam, cleaned.IsNeutral) = 
                    DetermineTeams(rawData["TeamName"].Trim(), 
                                 rawData["Opponent"].Trim(), 
                                 rawData["Location"].Trim());

                // Parse scores
                (cleaned.HomeScore, cleaned.VisitorScore) = 
                    ParseScores(rawData["Score"].Trim(), 
                              rawData["WL"].Trim(), 
                              cleaned.HomeTeam == rawData["TeamName"].Trim());

                // Calculate margin if we have both scores
                if (cleaned.HomeScore.HasValue && cleaned.VisitorScore.HasValue)
                {
                    cleaned.Margin = cleaned.HomeScore.Value - cleaned.VisitorScore.Value;
                }

                return cleaned;
            }
            catch (Exception ex)
            {
                throw new Exception($"Error cleaning game data: {ex.Message}", ex);
            }
        }

        private DateTime ParseGameDate(string dateStr, int season)
        {
            var parts = dateStr.Split('/');
            if (parts.Length != 2)
            {
                throw new FormatException($"Invalid date format: {dateStr}");
            }

            return new DateTime(season, 
                int.Parse(parts[0]), 
                int.Parse(parts[1]));
        }

        private (string homeTeam, string visitorTeam, bool isNeutral) DetermineTeams(
            string teamName, string opponent, string location)
        {
            bool isNeutral = string.IsNullOrEmpty(location);
            bool isAway = location == "@";
            
            // For now, using direct opponent name - will be replaced with URL lookup
            if (isAway)
            {
                return (opponent, teamName, isNeutral);
            }
            
            return (teamName, opponent, isNeutral);
        }

        private (int? homeScore, int? visitorScore) ParseScores(
            string score, string winLoss, bool isTeamNameHome)
        {
            if (string.IsNullOrEmpty(score)) 
                return (null, null);

            var parts = score.Split('-');
            if (parts.Length != 2)
                throw new FormatException($"Invalid score format: {score}");

            int score1 = int.Parse(parts[0]);
            int score2 = int.Parse(parts[1]);

            // If it's a tie, order doesn't matter
            if (score1 == score2)
                return (score1, score2);

            bool isWin = winLoss.Trim().ToUpper() == "W";
            
            // If TeamName is home team
            if (isTeamNameHome)
            {
                return isWin ? (score1, score2) : (score2, score1);
            }
            
            // If TeamName is visiting team
            return isWin ? (score2, score1) : (score1, score2);
        }
    }
}