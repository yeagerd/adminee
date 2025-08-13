type PageProps = {
  params: { token: string };
};

export default function PublicBookingPage({ params }: PageProps) {
  const { token } = params;
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">Public Booking</h1>
      <p className="text-sm text-muted-foreground">Token: {token}</p>
    </div>
  );
}


