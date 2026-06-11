-- Initial schema for Production Agent Platform

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    tenant_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) REFERENCES conversations(id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) REFERENCES conversations(id),
    tool_name VARCHAR(255) NOT NULL,
    input TEXT,
    output TEXT,
    latency_ms INTEGER,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approvals (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2),
    status VARCHAR(50) DEFAULT 'pending',
    reviewer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Indexes for Tenant isolation and performance
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_conversation ON tool_executions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_approvals_thread ON approvals(thread_id);

-- Seed Initial Users
INSERT INTO users (id, email, name, tenant_id, role) VALUES
('user_admin_1', 'admin@tenantA.com', 'Alice Admin', 'tenant_a', 'admin'),
('user_support_1', 'support@tenantA.com', 'Bob Support', 'tenant_a', 'support'),
('user_viewer_1', 'viewer@tenantA.com', 'Charlie Viewer', 'tenant_a', 'viewer'),
('user_admin_2', 'admin@tenantB.com', 'Dave Admin', 'tenant_b', 'admin'),
('user_support_2', 'support@tenantB.com', 'Eve Support', 'tenant_b', 'support')
ON CONFLICT (id) DO NOTHING;
