import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { purchasesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={purchasesModule} />;
}
