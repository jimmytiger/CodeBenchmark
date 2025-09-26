-- AI Evaluation Engine Database Schema

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Evaluations table
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    tasks TEXT[] NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    execution_time_seconds FLOAT,
    results JSONB,
    metrics_summary JSONB,
    analysis JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task results table
CREATE TABLE IF NOT EXISTS task_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    metrics JSONB,
    samples JSONB,
    execution_time_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    evaluation_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    labels JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_model ON evaluations(model_name);
CREATE INDEX IF NOT EXISTS idx_evaluations_start_time ON evaluations(start_time);
CREATE INDEX IF NOT EXISTS idx_task_results_evaluation_id ON task_results(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_task_results_task_name ON task_results(task_name);
CREATE INDEX IF NOT EXISTS idx_model_performance_model_task ON model_performance(model_name, task_name);
CREATE INDEX IF NOT EXISTS idx_model_performance_date ON model_performance(evaluation_date);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp ON system_metrics(metric_name, timestamp);

-- Create GIN index for JSONB columns
CREATE INDEX IF NOT EXISTS idx_evaluations_results_gin ON evaluations USING GIN(results);
CREATE INDEX IF NOT EXISTS idx_evaluations_metrics_gin ON evaluations USING GIN(metrics_summary);
CREATE INDEX IF NOT EXISTS idx_task_results_metrics_gin ON task_results USING GIN(metrics);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for evaluations table
DROP TRIGGER IF EXISTS update_evaluations_updated_at ON evaluations;
CREATE TRIGGER update_evaluations_updated_at
    BEFORE UPDATE ON evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW evaluation_summary AS
SELECT 
    e.evaluation_id,
    e.status,
    e.model_name,
    array_length(e.tasks, 1) as task_count,
    e.start_time,
    e.end_time,
    e.execution_time_seconds,
    COALESCE(jsonb_array_length(e.results), 0) as results_count,
    e.created_at
FROM evaluations e;

CREATE OR REPLACE VIEW model_performance_summary AS
SELECT 
    model_name,
    task_name,
    metric_name,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    STDDEV(metric_value) as std_dev,
    COUNT(*) as sample_count,
    MAX(evaluation_date) as last_evaluation
FROM model_performance
GROUP BY model_name, task_name, metric_name;

-- Insert initial data
INSERT INTO system_metrics (metric_name, metric_value, labels) VALUES
('system_initialized', 1, '{"version": "0.1.0", "component": "database"}')
ON CONFLICT DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_eval_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_eval_user;