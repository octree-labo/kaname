import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { salesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={salesModule} />;
}
