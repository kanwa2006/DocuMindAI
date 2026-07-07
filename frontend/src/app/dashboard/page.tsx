import { redirect } from "next/navigation";

// The original navigation surfaced /dashboard from the account dropdown and
// post-login. Until a dedicated dashboard exists, send users into the
// General workspace where they can start working immediately.
export default function DashboardPage() {
  redirect("/general");
}
