export default function Privacy() {
  return (
    <div className="min-h-screen bg-slate-900 px-6 py-12 max-w-3xl mx-auto text-slate-300">
      <h1 className="text-2xl font-bold text-white mb-2">Privacy Policy</h1>
      <p className="text-xs text-slate-500 mb-8">Last updated: draft — review with counsel before launch.</p>

      <div className="flex flex-col gap-6 text-sm leading-relaxed">
        <section>
          <h2 className="text-slate-200 font-semibold mb-2">1. What we collect</h2>
          <p>
            Account data: username, email, and password (stored hashed, never in plain text).
            Usage data: your saved country/region preferences, price-alert subscriptions, and
            requested reports. If you link a Telegram account, we store your Telegram chat ID to
            deliver notifications.
          </p>
        </section>

        <section>
          <h2 className="text-slate-200 font-semibold mb-2">2. What we don't collect</h2>
          <p>
            We do not collect payment information (no payment processing exists yet), and we do
            not sell personal data to third parties.
          </p>
        </section>

        <section>
          <h2 className="text-slate-200 font-semibold mb-2">3. How we use it</h2>
          <p>
            To operate your account, send the price alerts and reports you request, and to improve
            the product. We do not use your data for advertising.
          </p>
        </section>

        <section>
          <h2 className="text-slate-200 font-semibold mb-2">4. Third parties</h2>
          <p>
            Business-climate summaries are generated via a third-party LLM API (Groq). Price data
            is sourced from public listings on third-party sites (e.g. Airbnb, Booking.com).
            Notifications are delivered via Telegram if you opt in.
          </p>
        </section>

        <section>
          <h2 className="text-slate-200 font-semibold mb-2">5. Your rights</h2>
          <p>
            You can delete your subscriptions and reports at any time from the app. To delete your
            account entirely, contact the site administrator.
          </p>
        </section>
      </div>
    </div>
  )
}
