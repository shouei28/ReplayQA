export interface User {
  id: string;
  username: string;
  email: string;
}

export interface Project {
  id: string;
  name: string;
}

export interface Test {
  id: string;
  test_name: string;
  description: string;
  url: string;
  steps: StepDefinition[];
  expected_behavior: string;
  created_at: string;
  updated_at: string;
}

export interface StepDefinition {
  kind?: string;
  type?: string;
  instruction?: string;
  selector?: string;
  value?: string;
  url?: string;
  method?: string;
  target_coordinate?: string;
}

export interface TestExecution {
  id: string;
  test_id: string | null;
  test_name: string;
  description: string;
  url: string;
  steps: StepDefinition[];
  expected_behavior: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string | null;
  total_runtime_sec: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutedStep {
  step_number: number;
  instruction: string;
  type: string;
  status: "passed" | "failed" | "pending";
  error: string | null;
  screenshot_url?: string;
  timestamp?: string;
}

export interface TestResult {
  id: string;
  test_name: string;
  description: string;
  url: string;
  steps: StepDefinition[];
  expected_behavior: string;
  success: boolean;
  total_steps: number;
  passed_steps: number;
  executed_steps: ExecutedStep[];
  runtime_sec: number;
  started_at: string;
  total_tokens: number;
  explanation: string;
  agent_output: string;
  created_at: string;
  updated_at: string;
}

export interface RecorderSession {
  session_id: string;
  browserbase_session_id: string;
  connect_url: string;
  live_view_url: string;
}
