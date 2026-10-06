import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import DashboardClient from "./dashboard-client";

export default async function Home() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login");

  const meta = data.user.user_metadata ?? {};
  return (
    <DashboardClient
      user={{
        id: data.user.id,
        email: data.user.email ?? "",
        name: meta.full_name ?? meta.name ?? data.user.email?.split("@")[0] ?? "User",
        avatar: meta.avatar_url ?? meta.picture ?? "",
      }}
    />
  );
}
