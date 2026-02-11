export interface User {
  id: string;
  username: string;
  email: string;
}

export interface Project {
  id: string;
  name: string;
}

export interface TestExecution {
  id: string;
  status: string;
  test_name: string;
}

export interface RecorderSession {
  session_id: string;
  browserbase_session_id: string;
  connect_url: string;
  live_view_url: string;
}
