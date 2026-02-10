
CREATE PROCEDURE [dbo].[Get_Media_National_Champions]
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @Coef_Avg_Modified_Score DECIMAL(18, 5),
            @Coef_Win_Loss DECIMAL(18, 5),
            @Coef_Log_Score DECIMAL(18, 5);
    
    -- Fetch coefficients
    SELECT TOP 1 
        @Coef_Avg_Modified_Score = Avg_Adjusted_Margin_Coef,
        @Coef_Win_Loss = Power_Ranking_Coef_Win_Loss,
        @Coef_Log_Score = Power_Ranking_Coef
    FROM [dbo].[Coefficients]
    ORDER BY ID DESC;
    
    SELECT 
        m.Season AS [year],
        m.Team_Name AS team,
        tn.State AS [state],
        
        -- Record String
        CAST(ISNULL(m.Wins, 0) AS VARCHAR(10)) + '-' + 
        CAST(ISNULL(m.Losses, 0) AS VARCHAR(10)) + 
        CASE WHEN ISNULL(m.Ties, 0) > 0 THEN '-' + CAST(m.Ties AS VARCHAR(10)) ELSE '' END AS Record,
        
        -- Source
        m.Source_Code AS source_code,
        
        -- FIXED: Calculate ratings from HS_Rankings
        CAST(
            (ISNULL(r.Avg_Of_Avg_Of_Home_Modified_Score, 0) * @Coef_Avg_Modified_Score) +
            (ISNULL(r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) * @Coef_Win_Loss) +
            (ISNULL(r.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) * @Coef_Log_Score)
        AS DECIMAL(10,3)) AS combined,
        CAST(ISNULL(r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) AS DECIMAL(10,3)) AS margin,
        CAST(ISNULL(r.Max_Min_Margin, 0) AS DECIMAL(10,3)) AS win_loss,
        CAST(ISNULL(r.Offense, 0) AS DECIMAL(10,3)) AS offense,
        CAST(ISNULL(r.Defense, 0) AS DECIMAL(10,3)) AS defense,
        
        -- Total Games
        (ISNULL(m.Wins, 0) + ISNULL(m.Losses, 0) + ISNULL(m.Ties, 0)) AS games_played,
        
        -- Coach and Notes
        m.Coach_ID AS coach,
        m.Notes AS notes,
        
        -- Team Metadata
        tn.LogoURL AS logoURL,
        tn.School_Logo_URL AS schoolLogoURL,
        ISNULL(tn.PrimaryColor, '#003366') AS backgroundColor,
        ISNULL(tn.SecondaryColor, '#FFD700') AS secondaryColor,
        ISNULL(tn.SecondaryColor, '#FFFFFF') AS textColor,
        tn.Mascot AS mascot,
        
        -- Team Page Linking
        m.Team_ID AS teamId,
        CASE 
            WHEN tn.Team_Page_URL IS NOT NULL AND tn.Team_Page_URL <> '' THEN 1
            ELSE ISNULL(tn.Has_Team_Page, 0)
        END AS HasTeamPage,
        tn.Team_Page_URL AS TeamPageUrl
        
    FROM 
        Media_National_Champions m
    LEFT JOIN 
        HS_Team_Names tn ON m.Team_ID = tn.ID
    LEFT JOIN
        HS_Rankings r ON m.Team_Name = r.Home AND m.Season = r.Season AND r.Week = 52
    ORDER BY 
        m.Season DESC;
END
