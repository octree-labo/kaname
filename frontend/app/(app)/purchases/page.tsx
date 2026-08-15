import { DocumentListPage } from "@/components/document/DocumentListPage";
import { purchasesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={purchasesModule} />;
}
