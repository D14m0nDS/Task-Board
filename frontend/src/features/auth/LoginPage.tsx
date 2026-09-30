import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate } from "react-router-dom";

import { useAuth } from "./useAuth";

export function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const loginMutation = useMutation({
    mutationFn: () => login(email, password),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    loginMutation.mutate();
  }

  if (user !== null) {
    return <Navigate to="/" replace />;
  }

  return (
    <main className="card">
      <h1>Sign in</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button type="submit" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {loginMutation.isError && (
        <p className="error" role="alert">
          {loginMutation.error.message}
        </p>
      )}

      <p className="hint">
        No account yet? <Link to="/register">Create one</Link>
      </p>
    </main>
  );
}
