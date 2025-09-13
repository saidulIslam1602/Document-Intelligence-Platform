-- Advanced Stream Analytics Queries for Document Intelligence Platform
-- Real-time processing and analytics using Azure Stream Analytics

-- =============================================
-- Document Processing Metrics Query
-- =============================================
WITH DocumentProcessingMetrics AS (
    SELECT 
        System.Timestamp() AS ProcessingTime,
        DocumentId,
        DocumentType,
        ProcessingDuration,
        CASE 
            WHEN ProcessingDuration < 5000 THEN 'Fast'
            WHEN ProcessingDuration < 15000 THEN 'Medium'
            ELSE 'Slow'
        END AS ProcessingCategory,
        Success,
        ErrorMessage,
        UserId,
        FileSize,
        Confidence
    FROM DocumentProcessingStream
    WHERE System.Timestamp() >= DATEADD(minute, -5, System.Timestamp())
),

-- =============================================
-- Real-time Performance Metrics
-- =============================================
PerformanceMetrics AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        COUNT(*) AS TotalDocuments,
        AVG(ProcessingDuration) AS AvgProcessingDuration,
        MAX(ProcessingDuration) AS MaxProcessingDuration,
        MIN(ProcessingDuration) AS MinProcessingDuration,
        SUM(CASE WHEN Success = 1 THEN 1 ELSE 0 END) AS SuccessfulDocuments,
        SUM(CASE WHEN Success = 0 THEN 1 ELSE 0 END) AS FailedDocuments,
        AVG(Confidence) AS AvgConfidence,
        AVG(FileSize) AS AvgFileSize
    FROM DocumentProcessingStream
    GROUP BY TumblingWindow(minute, 1)
),

-- =============================================
-- Document Type Distribution
-- =============================================
DocumentTypeDistribution AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        DocumentType,
        COUNT(*) AS DocumentCount,
        AVG(ProcessingDuration) AS AvgProcessingDuration,
        AVG(Confidence) AS AvgConfidence,
        SUM(CASE WHEN Success = 1 THEN 1 ELSE 0 END) AS SuccessCount,
        SUM(CASE WHEN Success = 0 THEN 1 ELSE 0 END) AS FailureCount
    FROM DocumentProcessingStream
    GROUP BY TumblingWindow(minute, 5), DocumentType
),

-- =============================================
-- Sentiment Analysis Trends
-- =============================================
SentimentTrends AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        Sentiment,
        DocumentType,
        COUNT(*) AS DocumentCount,
        AVG(SentimentScore) AS AvgSentimentScore,
        AVG(Confidence) AS AvgConfidence
    FROM DocumentProcessingStream
    WHERE Sentiment IS NOT NULL
    GROUP BY TumblingWindow(minute, 5), Sentiment, DocumentType
),

-- =============================================
-- Language Detection Analytics
-- =============================================
LanguageAnalytics AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        DetectedLanguage,
        COUNT(*) AS DocumentCount,
        AVG(ProcessingDuration) AS AvgProcessingDuration,
        AVG(Confidence) AS AvgConfidence,
        SUM(CASE WHEN Success = 1 THEN 1 ELSE 0 END) AS SuccessCount
    FROM DocumentProcessingStream
    WHERE DetectedLanguage IS NOT NULL
    GROUP BY TumblingWindow(minute, 5), DetectedLanguage
),

-- =============================================
-- Error Analysis and Alerting
-- =============================================
ErrorAnalysis AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        ErrorCode,
        ErrorMessage,
        DocumentType,
        COUNT(*) AS ErrorCount,
        AVG(ProcessingDuration) AS AvgProcessingDurationBeforeError
    FROM DocumentProcessingStream
    WHERE Success = 0
    GROUP BY TumblingWindow(minute, 1), ErrorCode, ErrorMessage, DocumentType
),

-- =============================================
-- User Activity Analytics
-- =============================================
UserActivity AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        UserId,
        COUNT(*) AS DocumentsProcessed,
        AVG(ProcessingDuration) AS AvgProcessingDuration,
        SUM(FileSize) AS TotalFileSize,
        COUNT(DISTINCT DocumentType) AS UniqueDocumentTypes,
        AVG(Confidence) AS AvgConfidence
    FROM DocumentProcessingStream
    WHERE UserId IS NOT NULL
    GROUP BY TumblingWindow(minute, 10), UserId
),

-- =============================================
-- Anomaly Detection for Processing Duration
-- =============================================
ProcessingDurationAnomalies AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        DocumentId,
        ProcessingDuration,
        DocumentType,
        UserId,
        CASE 
            WHEN ProcessingDuration > (SELECT AVG(ProcessingDuration) + 2 * STDEV(ProcessingDuration) 
                                     FROM DocumentProcessingStream 
                                     WHERE System.Timestamp() >= DATEADD(hour, -1, System.Timestamp())) 
            THEN 1 
            ELSE 0 
        END AS IsAnomaly
    FROM DocumentProcessingStream
    WHERE ProcessingDuration > 0
),

-- =============================================
-- Throughput Analysis
-- =============================================
ThroughputAnalysis AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        COUNT(*) AS DocumentsPerMinute,
        AVG(ProcessingDuration) AS AvgProcessingDuration,
        SUM(FileSize) AS TotalDataProcessed,
        COUNT(DISTINCT UserId) AS ActiveUsers,
        COUNT(DISTINCT DocumentType) AS DocumentTypesProcessed
    FROM DocumentProcessingStream
    GROUP BY TumblingWindow(minute, 1)
),

-- =============================================
-- Quality Metrics
-- =============================================
QualityMetrics AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        DocumentType,
        AVG(Confidence) AS AvgConfidence,
        COUNT(CASE WHEN Confidence >= 0.9 THEN 1 END) AS HighConfidenceDocs,
        COUNT(CASE WHEN Confidence >= 0.7 AND Confidence < 0.9 THEN 1 END) AS MediumConfidenceDocs,
        COUNT(CASE WHEN Confidence < 0.7 THEN 1 END) AS LowConfidenceDocs,
        COUNT(*) AS TotalDocs
    FROM DocumentProcessingStream
    WHERE Confidence IS NOT NULL
    GROUP BY TumblingWindow(minute, 5), DocumentType
),

-- =============================================
-- Entity Extraction Analytics
-- =============================================
EntityExtractionAnalytics AS (
    SELECT 
        System.Timestamp() AS WindowEnd,
        DocumentType,
        EntityType,
        COUNT(*) AS EntityCount,
        AVG(EntityConfidence) AS AvgEntityConfidence,
        COUNT(DISTINCT DocumentId) AS DocumentsWithEntity
    FROM DocumentProcessingStream
    CROSS APPLY GetArrayElements(Entities) AS Entity
    WHERE Entity.ArrayValue.EntityType IS NOT NULL
    GROUP BY TumblingWindow(minute, 5), DocumentType, EntityType
),

-- =============================================
-- Real-time Alerts
-- =============================================
RealTimeAlerts AS (
    SELECT 
        System.Timestamp() AS AlertTime,
        'HighFailureRate' AS AlertType,
        'High failure rate detected' AS AlertMessage,
        DocumentType,
        COUNT(*) AS FailureCount,
        COUNT(*) * 100.0 / (COUNT(*) + SUM(CASE WHEN Success = 1 THEN 1 ELSE 0 END)) AS FailureRate
    FROM DocumentProcessingStream
    WHERE Success = 0
    GROUP BY TumblingWindow(minute, 1), DocumentType
    HAVING COUNT(*) * 100.0 / (COUNT(*) + SUM(CASE WHEN Success = 1 THEN 1 ELSE 0 END)) > 10
    
    UNION ALL
    
    SELECT 
        System.Timestamp() AS AlertTime,
        'SlowProcessing' AS AlertType,
        'Processing duration exceeds threshold' AS AlertMessage,
        DocumentType,
        COUNT(*) AS SlowProcessingCount,
        AVG(ProcessingDuration) AS AvgProcessingDuration
    FROM DocumentProcessingStream
    WHERE ProcessingDuration > 30000  -- 30 seconds
    GROUP BY TumblingWindow(minute, 1), DocumentType
    HAVING COUNT(*) > 5
    
    UNION ALL
    
    SELECT 
        System.Timestamp() AS AlertTime,
        'LowConfidence' AS AlertType,
        'Low confidence scores detected' AS AlertMessage,
        DocumentType,
        COUNT(*) AS LowConfidenceCount,
        AVG(Confidence) AS AvgConfidence
    FROM DocumentProcessingStream
    WHERE Confidence < 0.5
    GROUP BY TumblingWindow(minute, 1), DocumentType
    HAVING COUNT(*) > 3
)

-- =============================================
-- Main Output Queries
-- =============================================

-- Output 1: Real-time Dashboard Data
SELECT 
    WindowEnd AS Timestamp,
    TotalDocuments,
    SuccessfulDocuments,
    FailedDocuments,
    AvgProcessingDuration,
    AvgConfidence,
    (SuccessfulDocuments * 100.0 / TotalDocuments) AS SuccessRate,
    AvgFileSize
INTO PowerBIDashboard
FROM PerformanceMetrics;

-- Output 2: Document Type Analytics
SELECT 
    WindowEnd AS Timestamp,
    DocumentType,
    DocumentCount,
    AvgProcessingDuration,
    AvgConfidence,
    SuccessCount,
    FailureCount,
    (SuccessCount * 100.0 / DocumentCount) AS SuccessRate
INTO DocumentTypeAnalytics
FROM DocumentTypeDistribution;

-- Output 3: Sentiment Trends
SELECT 
    WindowEnd AS Timestamp,
    Sentiment,
    DocumentType,
    DocumentCount,
    AvgSentimentScore,
    AvgConfidence
INTO SentimentAnalytics
FROM SentimentTrends;

-- Output 4: Language Analytics
SELECT 
    WindowEnd AS Timestamp,
    DetectedLanguage,
    DocumentCount,
    AvgProcessingDuration,
    AvgConfidence,
    SuccessCount,
    (SuccessCount * 100.0 / DocumentCount) AS SuccessRate
INTO LanguageAnalytics
FROM LanguageAnalytics;

-- Output 5: Error Analysis
SELECT 
    WindowEnd AS Timestamp,
    ErrorCode,
    ErrorMessage,
    DocumentType,
    ErrorCount,
    AvgProcessingDurationBeforeError
INTO ErrorAnalytics
FROM ErrorAnalysis;

-- Output 6: User Activity
SELECT 
    WindowEnd AS Timestamp,
    UserId,
    DocumentsProcessed,
    AvgProcessingDuration,
    TotalFileSize,
    UniqueDocumentTypes,
    AvgConfidence
INTO UserActivityAnalytics
FROM UserActivity;

-- Output 7: Anomaly Detection
SELECT 
    WindowEnd AS Timestamp,
    DocumentId,
    ProcessingDuration,
    DocumentType,
    UserId,
    IsAnomaly
INTO AnomalyDetection
FROM ProcessingDurationAnomalies
WHERE IsAnomaly = 1;

-- Output 8: Throughput Analysis
SELECT 
    WindowEnd AS Timestamp,
    DocumentsPerMinute,
    AvgProcessingDuration,
    TotalDataProcessed,
    ActiveUsers,
    DocumentTypesProcessed
INTO ThroughputAnalytics
FROM ThroughputAnalysis;

-- Output 9: Quality Metrics
SELECT 
    WindowEnd AS Timestamp,
    DocumentType,
    AvgConfidence,
    HighConfidenceDocs,
    MediumConfidenceDocs,
    LowConfidenceDocs,
    TotalDocs,
    (HighConfidenceDocs * 100.0 / TotalDocs) AS HighConfidenceRate
INTO QualityMetrics
FROM QualityMetrics;

-- Output 10: Entity Extraction Analytics
SELECT 
    WindowEnd AS Timestamp,
    DocumentType,
    EntityType,
    EntityCount,
    AvgEntityConfidence,
    DocumentsWithEntity
INTO EntityAnalytics
FROM EntityExtractionAnalytics;

-- Output 11: Real-time Alerts
SELECT 
    AlertTime AS Timestamp,
    AlertType,
    AlertMessage,
    DocumentType,
    FailureCount,
    FailureRate
INTO RealTimeAlerts
FROM RealTimeAlerts;

-- =============================================
-- Advanced Analytics Queries
-- =============================================

-- Moving Average of Processing Duration
SELECT 
    System.Timestamp() AS WindowEnd,
    DocumentType,
    AVG(ProcessingDuration) AS CurrentAvg,
    AVG(AVG(ProcessingDuration)) OVER (
        PARTITION BY DocumentType 
        ORDER BY System.Timestamp() 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) AS MovingAvg5Min,
    AVG(AVG(ProcessingDuration)) OVER (
        PARTITION BY DocumentType 
        ORDER BY System.Timestamp() 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) AS MovingAvg10Min
FROM DocumentProcessingStream
GROUP BY TumblingWindow(minute, 1), DocumentType;

-- Trend Analysis
SELECT 
    System.Timestamp() AS WindowEnd,
    DocumentType,
    COUNT(*) AS DocumentCount,
    LAG(COUNT(*), 1) OVER (PARTITION BY DocumentType ORDER BY System.Timestamp()) AS PreviousCount,
    COUNT(*) - LAG(COUNT(*), 1) OVER (PARTITION BY DocumentType ORDER BY System.Timestamp()) AS Trend
FROM DocumentProcessingStream
GROUP BY TumblingWindow(minute, 5), DocumentType;

-- Peak Usage Analysis
SELECT 
    System.Timestamp() AS WindowEnd,
    COUNT(*) AS DocumentsProcessed,
    COUNT(DISTINCT UserId) AS ActiveUsers,
    AVG(ProcessingDuration) AS AvgProcessingDuration,
    CASE 
        WHEN COUNT(*) > (SELECT AVG(COUNT(*)) FROM DocumentProcessingStream 
                        GROUP BY TumblingWindow(minute, 1)) * 1.5 
        THEN 'Peak' 
        ELSE 'Normal' 
    END AS UsageLevel
FROM DocumentProcessingStream
GROUP BY TumblingWindow(minute, 1);